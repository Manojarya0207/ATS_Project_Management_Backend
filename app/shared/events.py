"""In-process domain event bus.

Decouples modules: e.g. the tasks service publishes :class:`TaskAssigned`
without importing the notifications service; the notifications module
subscribes in its ``handlers.py`` during application startup.

Handlers receive the publisher's ``AsyncSession`` so their writes commit
atomically with the triggering change. Swapping ``publish`` for an
enqueue-to-broker implementation (see ``app.infrastructure.queue``) turns these
into asynchronous background jobs without touching any publisher.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.events")


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""


@dataclass(frozen=True)
class MemberAddedToProject(DomainEvent):
    project_id: uuid.UUID
    project_name: str
    user_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass(frozen=True)
class TaskAssigned(DomainEvent):
    task_id: uuid.UUID
    task_title: str
    project_name: str
    assignee_id: uuid.UUID
    actor_id: uuid.UUID


EventHandler = Callable[[DomainEvent, AsyncSession], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent, db: AsyncSession) -> None:
        for handler in self._handlers[type(event)]:
            logger.debug("Dispatching %s to %s", type(event).__name__, handler.__qualname__)
            await handler(event, db)
