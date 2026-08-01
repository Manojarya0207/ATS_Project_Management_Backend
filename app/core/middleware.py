"""ASGI middleware: request context (request/correlation IDs), request timing
and access logging, and security response headers.

Registration order matters (Starlette wraps middleware LIFO): CORS must be
added *last* in :func:`app.main.create_app` so it is the outermost layer and
its headers apply to error responses too.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import (
    CORRELATION_ID_HEADER,
    PROCESS_TIME_HEADER,
    REQUEST_ID_HEADER,
)
from app.core.logging import correlation_id_var, request_id_var

access_logger = logging.getLogger("app.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID and propagate/generate a correlation ID.

    - Request ID: generated per request; returned in ``X-Request-ID``.
    - Correlation ID: taken from the incoming ``X-Correlation-ID`` header when a
      caller (gateway, upstream service) provides one, else equal to the
      request ID. Enables cross-service tracing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = uuid.uuid4().hex
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        rid_token = request_id_var.set(request_id)
        cid_token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(rid_token)
            correlation_id_var.reset(cid_token)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured access + performance logging for every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers[PROCESS_TIME_HEADER] = str(duration_ms)

        access_logger.info(
            "%s %s -> %s (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
            },
        )
        return response


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security headers for an API (no HTML content served)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Cache-Control", "no-store" if request.url.path.startswith("/api") else "no-cache"
        )
        return response
