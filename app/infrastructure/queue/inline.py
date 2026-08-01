"""Inline queue: executes jobs immediately in-process (no broker required)."""

from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.queue import JobHandler

logger = logging.getLogger("app.queue")


class InlineQueue:
    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, name: str, handler: JobHandler) -> None:
        self._handlers[name] = handler

    async def enqueue(self, name: str, /, **kwargs: Any) -> None:
        handler = self._handlers.get(name)
        if handler is None:
            logger.warning("No handler registered for job %r — dropping", name)
            return
        await handler(**kwargs)
