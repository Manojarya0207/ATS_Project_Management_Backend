"""Notification model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPkMixin
from app.shared.enums import NotificationType

if TYPE_CHECKING:
    from app.modules.users.models import User


class Notification(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", native_enum=False, length=32),
        default=NotificationType.general,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="notifications", lazy="raise")

    # Unread-badge query: WHERE user_id = ? AND is_read = false
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)
