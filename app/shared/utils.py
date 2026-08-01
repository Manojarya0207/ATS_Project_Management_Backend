"""Small dependency-free helpers shared across the codebase."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import uuid_utils


def uuid7() -> uuid.UUID:
    """Generate a time-ordered UUIDv7 as a stdlib ``uuid.UUID``.

    UUIDv7 keeps B-tree indexes append-mostly (unlike random v4), which matters
    at scale. We convert from ``uuid_utils`` to the stdlib type so SQLAlchemy
    and Pydantic see a plain ``uuid.UUID``.
    """
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)


def utcnow() -> datetime:
    """Timezone-aware current time in UTC. Always prefer this over naive now()."""
    return datetime.now(UTC)
