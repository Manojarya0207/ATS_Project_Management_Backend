"""Background job queue abstraction.

Callers enqueue named jobs through the :class:`TaskQueue` protocol. The default
``inline`` implementation executes the job immediately (awaited in-request) —
correct behaviour today with zero infrastructure. When workloads justify it,
switch ``QUEUE_BACKEND=celery`` and register the same handler names as Celery
tasks: no calling code changes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from app.core.config import Settings

JobHandler = Callable[..., Awaitable[Any]]


@runtime_checkable
class TaskQueue(Protocol):
    def register(self, name: str, handler: JobHandler) -> None:
        """Register a coroutine as the handler for ``name``."""
        ...

    async def enqueue(self, name: str, /, **kwargs: Any) -> None:
        """Schedule the named job with keyword arguments (JSON-serializable)."""
        ...


def get_queue(settings: Settings) -> TaskQueue:
    backend = settings.queue_backend.lower()
    if backend == "inline":
        from app.infrastructure.queue.inline import InlineQueue

        return InlineQueue()
    if backend == "celery":
        from app.infrastructure.queue.celery import CeleryQueue

        return CeleryQueue(settings)
    raise ValueError(f"Unknown queue backend: {settings.queue_backend!r}")
