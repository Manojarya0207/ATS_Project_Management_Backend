"""Refresh token model.

Tokens are opaque random strings; only their SHA-256 hash is persisted.
``family_id`` groups a rotation chain — when a rotated (already-revoked) token
is presented again, the entire family is revoked (reuse detection).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPkMixin
from app.shared.utils import uuid7

if TYPE_CHECKING:
    from app.modules.users.models import User


class RefreshToken(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid7, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)

    user: Mapped[User] = relationship(back_populates="refresh_tokens", lazy="raise")
