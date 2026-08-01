"""Rate limiting (slowapi).

The ``Limiter`` instance must exist at import time for route decorators, but
its behaviour (enabled flag, limit values) is configured from ``Settings``
during application startup via :func:`configure` — limits are declared as
callables so they always read the configured value.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import Settings

limiter = Limiter(key_func=get_remote_address)

_auth_limit = "10/minute"


def auth_rate_limit() -> str:
    """Callable limit value for auth endpoints (login/register/refresh)."""
    return _auth_limit


def configure(settings: Settings) -> None:
    global _auth_limit
    _auth_limit = settings.rate_limit_auth
    limiter.enabled = settings.rate_limit_enabled
