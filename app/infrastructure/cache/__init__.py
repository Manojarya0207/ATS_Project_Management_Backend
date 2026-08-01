"""Cache abstraction.

Services depend on the :class:`CacheBackend` protocol; the implementation is
selected by ``Settings.cache_backend`` (``memory`` today, ``redis`` when a
Redis instance is provisioned, ``none`` to disable). Values are JSON-serialized
by callers where needed; the cache stores/returns strings.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.config import Settings


@runtime_checkable
class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def clear(self) -> None: ...

    async def close(self) -> None: ...


def get_cache(settings: Settings) -> CacheBackend:
    backend = settings.cache_backend.lower()
    if backend == "memory":
        from app.infrastructure.cache.memory import InMemoryCache

        return InMemoryCache()
    if backend == "none":
        from app.infrastructure.cache.memory import NullCache

        return NullCache()
    if backend == "redis":
        from app.infrastructure.cache.redis import RedisCache

        return RedisCache(settings)
    raise ValueError(f"Unknown cache backend: {settings.cache_backend!r}")
