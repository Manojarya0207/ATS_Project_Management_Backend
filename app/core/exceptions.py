"""Centralized application exception hierarchy and FastAPI exception handlers.

All errors leave the API as the standard envelope with ``success: false`` and
one or more machine-readable ``errors[].code`` values (see
:class:`app.core.constants.ErrorCode`). Services raise :class:`AppException`
subclasses; nothing outside this module builds error responses by hand.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.constants import ErrorCode
from app.shared.responses import ErrorDetail, error_body

logger = logging.getLogger("app.errors")


class AppException(Exception):
    """Base class for all expected application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: ErrorCode = ErrorCode.internal_error

    def __init__(
        self,
        detail: str = "Internal server error",
        *,
        code: ErrorCode | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code
        self.field = field


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = ErrorCode.not_found

    def __init__(self, detail: str = "Resource not found", **kw: Any) -> None:
        super().__init__(detail, **kw)


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.unauthorized

    def __init__(self, detail: str = "Not authenticated", **kw: Any) -> None:
        super().__init__(detail, **kw)


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.forbidden

    def __init__(self, detail: str = "Not authorized", **kw: Any) -> None:
        super().__init__(detail, **kw)


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = ErrorCode.conflict

    def __init__(self, detail: str = "Conflict", **kw: Any) -> None:
        super().__init__(detail, **kw)


class ValidationAppError(AppException):
    status_code = 422
    code = ErrorCode.validation_error

    def __init__(self, detail: str = "Validation error", **kw: Any) -> None:
        super().__init__(detail, **kw)


def _json(status_code: int, message: str, errors: list[ErrorDetail]) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code, content=error_body(message, errors), headers=headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return _json(
            exc.status_code,
            exc.detail,
            [ErrorDetail(code=exc.code, detail=exc.detail, field=exc.field)],
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Envelope framework-raised HTTPExceptions (e.g. OAuth2 401s, 404s)."""
        code = {
            401: ErrorCode.unauthorized,
            403: ErrorCode.forbidden,
            404: ErrorCode.not_found,
            405: ErrorCode.validation_error,
            409: ErrorCode.conflict,
        }.get(exc.status_code, ErrorCode.internal_error)
        detail = str(exc.detail) if exc.detail else "Request failed"
        return _json(exc.status_code, detail, [ErrorDetail(code=code, detail=detail)])

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            ErrorDetail(
                code=ErrorCode.validation_error,
                detail=e.get("msg", "Invalid value"),
                field=".".join(str(loc) for loc in e.get("loc", []) if loc != "body") or None,
            )
            for e in exc.errors()
        ]
        return _json(422, "Validation failed", errors)

    @app.exception_handler(StaleDataError)
    async def handle_stale_data(request: Request, exc: StaleDataError) -> JSONResponse:
        return _json(
            status.HTTP_409_CONFLICT,
            "The resource was modified by another request; retry with fresh data",
            [ErrorDetail(code=ErrorCode.stale_version, detail=str(exc))],
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc)
        return _json(
            status.HTTP_409_CONFLICT,
            "The request conflicts with existing data",
            [ErrorDetail(code=ErrorCode.conflict, detail="Database constraint violated")],
        )

    @app.exception_handler(RateLimitExceeded)
    async def handle_rate_limit(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _json(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests",
            [ErrorDetail(code=ErrorCode.rate_limited, detail=f"Rate limit exceeded: {exc.detail}")],
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _json(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            [ErrorDetail(code=ErrorCode.internal_error, detail="An unexpected error occurred")],
        )
