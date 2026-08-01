"""Health, liveness, and readiness endpoints.

- ``GET /health``       — basic check (backwards compatible with v1).
- ``GET /health/live``  — liveness: process is up (no dependencies checked).
- ``GET /health/ready`` — readiness: verifies database connectivity; returns
  503 while dependencies are unavailable so orchestrators hold traffic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.shared.responses import ok

logger = logging.getLogger("app.health")

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return ok({"status": "ok"}, message="Service healthy")


@router.get("/health/live")
async def liveness() -> dict[str, Any]:
    return ok({"status": "alive"})


@router.get("/health/ready")
async def readiness(request: Request) -> Any:
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with request.app.state.sessionmaker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Readiness check failed: database unreachable")
        checks["database"] = "unavailable"
        healthy = False

    if not healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "message": "Service not ready",
                "data": {"checks": checks},
                "meta": None,
                "errors": [],
            },
        )
    return ok({"checks": checks}, message="Service ready")
