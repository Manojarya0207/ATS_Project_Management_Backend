"""In-process cache implementations: a TTL dict cache and a no-op cache.

The in-memory cache is per-process (not shared across workers) — suitable for
development and small deployments. Production should use the Redis backend.
"""

from __future__ import annotations

import time


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()

    async def close(self) -> None:
        self._store.clear()


class NullCache:
    """Disables caching entirely (``CACHE_BACKEND=none``)."""

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None

    async def clear(self) -> None:
        return None

    async def close(self) -> None:
        return None
