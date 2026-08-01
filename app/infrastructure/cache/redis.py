"""Redis cache backend.

Requires the optional ``redis`` dependency group (``pip install .[redis]``)
and ``CACHE_BACKEND=redis`` + ``REDIS_URL``.
"""

from __future__ import annotations

from app.core.config import Settings


class RedisCache:
    def __init__(self, settings: Settings) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Redis cache requires redis — install with: pip install '.[redis]'"
            ) from exc
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        await self._client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def clear(self) -> None:
        await self._client.flushdb()

    async def close(self) -> None:
        await self._client.aclose()
