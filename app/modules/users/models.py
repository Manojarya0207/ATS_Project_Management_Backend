"""User model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin
from app.shared.enums import UserRole

if TYPE_CHECKING:
    from app.modules.auth.models import RefreshToken
    from app.modules.notifications.models import Notification
    from app.modules.projects.models import ProjectMember


class User(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=32),
        default=UserRole.employee,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )
    memberships: Mapped[list[ProjectMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )

    # Email uniqueness applies to *live* rows only: a soft-deleted user's email
    # may be re-registered. Partial unique index works on both PG and SQLite.
    __table_args__ = (
        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
