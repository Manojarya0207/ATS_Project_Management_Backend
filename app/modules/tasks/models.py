"""Task, Comment, and FileAttachment models.

Task carries an optimistic-locking ``version`` column: concurrent updates to
the same task (two users dragging the same kanban card) raise
``StaleDataError``, surfaced to clients as ``409 STALE_VERSION``.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin
from app.shared.enums import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from app.modules.projects.models import Project
    from app.modules.users.models import User


class Task(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", native_enum=False, length=32),
        default=TaskStatus.todo,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", native_enum=False, length=32),
        default=TaskPriority.medium,
        nullable=False,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, default=None, index=True)
    position: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 — SQLAlchemy mapper config

    project: Mapped[Project] = relationship(back_populates="tasks", lazy="raise")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id], lazy="raise")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="raise"
    )
    files: Mapped[list[FileAttachment]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="raise"
    )

    # Kanban column fetch: WHERE project_id = ? [AND status = ?] ORDER BY position
    __table_args__ = (
        Index("ix_tasks_project_status_position", "project_id", "status", "position"),
    )


class Comment(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped[Task] = relationship(back_populates="comments", lazy="raise")
    user: Mapped[User] = relationship(lazy="raise")


class FileAttachment(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "file_attachments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), default=None)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    task: Mapped[Task] = relationship(back_populates="files", lazy="raise")
    uploader: Mapped[User] = relationship(lazy="raise")
