"""Structured logging configuration.

- JSON logs in staging/production (machine-parseable for ELK/Loki/CloudWatch),
  human-readable console logs in development.
- Every record is enriched with the current request ID and correlation ID from
  contextvars set by :class:`app.core.middleware.RequestContextMiddleware`, so
  all log lines emitted while handling a request are traceable.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.correlation_id = correlation_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if rid := getattr(record, "request_id", None):
            entry["request_id"] = rid
        if cid := getattr(record, "correlation_id", None):
            entry["correlation_id"] = cid
        # Attach structured extras (anything passed via logger.info(..., extra={...}))
        for key in ("method", "path", "status_code", "duration_ms", "user_id", "client"):
            value = getattr(record, key, None)
            if value is not None:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rid = getattr(record, "request_id", None)
        prefix = f"[{rid[:8]}] " if rid else ""
        base = (
            f"{self.formatTime(record, '%H:%M:%S')} "
            f"{record.levelname:<8} {record.name}: {prefix}{record.getMessage()}"
        )
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_json_enabled else ConsoleFormatter())
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # Quiet noisy third-party loggers; uvicorn access logs are superseded by
    # our own request logging middleware.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
