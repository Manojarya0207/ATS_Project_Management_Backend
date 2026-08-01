"""Core dependency providers.

Everything is resolved from ``app.state`` (populated in the lifespan) — there
are no module-level singletons, which keeps tests and scripts free to build
their own object graphs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.infrastructure.cache import CacheBackend
from app.infrastructure.queue import TaskQueue
from app.infrastructure.storage import StorageBackend
from app.shared.events import EventBus


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Request-scoped session: commits on success, rolls back on error."""
    async with request.app.state.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage


def get_cache(request: Request) -> CacheBackend:
    return request.app.state.cache


def get_queue(request: Request) -> TaskQueue:
    return request.app.state.queue


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
StorageDep = Annotated[StorageBackend, Depends(get_storage)]
CacheDep = Annotated[CacheBackend, Depends(get_cache)]
QueueDep = Annotated[TaskQueue, Depends(get_queue)]
EventBusDep = Annotated[EventBus, Depends(get_event_bus)]
