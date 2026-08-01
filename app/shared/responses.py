"""Standard API response envelope.

Every JSON endpoint returns::

    {"success": true, "message": "...", "data": ..., "meta": {...}, "errors": []}

Success responses are built with :func:`ok`; error responses are produced
exclusively by the exception handlers in :mod:`app.core.exceptions` so the
shape is enforced in one place. Routers declare ``response_model=ApiResponse[T]``
which keeps the OpenAPI/Swagger schema truthful (a middleware-based wrapper
would document the wrong shape).

Deliberate exceptions to the envelope:
- ``204 No Content`` responses have no body by definition.
- File downloads return a raw ``FileResponse`` (binary stream).
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    detail: str
    field: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str | None = None
    data: T | None = None
    meta: dict[str, Any] | None = None
    errors: list[ErrorDetail] = []


def ok(
    data: Any = None,
    message: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a success envelope. Returned as a dict so FastAPI validates it
    against the route's declared ``response_model=ApiResponse[T]``."""
    return {"success": True, "message": message, "data": data, "meta": meta, "errors": []}


def error_body(
    message: str,
    errors: list[ErrorDetail] | None = None,
) -> dict[str, Any]:
    """Build a failure envelope (used only by exception handlers)."""
    return {
        "success": False,
        "message": message,
        "data": None,
        "meta": None,
        "errors": [e.model_dump() for e in (errors or [])],
    }
