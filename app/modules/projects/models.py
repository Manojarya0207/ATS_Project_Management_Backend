"""Project and ProjectMember models."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin
from app.shared.enums import MemberRole, ProjectStatus

if TYPE_CHECKING:
    from app.modules.tasks.models import Task
    from app.modules.users.models import User


class Project(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status", native_enum=False, length=32),
        default=ProjectStatus.planning,
        nullable=False,
        index=True,
    )
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    members: Mapped[list[ProjectMember]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="raise"
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="raise"
    )
    creator: Mapped[User] = relationship(foreign_keys=[created_by], lazy="raise")


class ProjectMember(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role", native_enum=False, length=32),
        default=MemberRole.contributor,
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="members", lazy="raise")
    user: Mapped[User] = relationship(back_populates="memberships", lazy="raise")

    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)
