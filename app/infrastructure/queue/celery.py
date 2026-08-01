"""Celery queue adapter.

Requires the optional ``celery`` dependency group and a broker (Redis/RabbitMQ).
``enqueue`` dispatches by task name via ``send_task``; workers must define
tasks with the same names. Handlers registered here are ignored (workers own
execution) — kept so the call sites remain identical to the inline queue.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.infrastructure.queue import JobHandler


class CeleryQueue:
    def __init__(self, settings: Settings) -> None:
        try:
            from celery import Celery
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Celery queue requires celery — install with: pip install '.[celery]'"
            ) from exc
        self._app = Celery("ats_pm", broker=settings.redis_url, backend=settings.redis_url)

    def register(self, name: str, handler: JobHandler) -> None:
        # Workers register tasks on their side; the API process only sends.
        return None

    async def enqueue(self, name: str, /, **kwargs: Any) -> None:
        self._app.send_task(name, kwargs=kwargs)
