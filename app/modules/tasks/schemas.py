"""Task, comment, and file schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.schemas import UserOut
from app.shared.enums import TaskPriority, TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: uuid.UUID | None
    assignee: UserOut | None
    due_date: date | None
    position: float
    created_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """Partial update. Deliberately excludes ``status``/``position`` —
    kanban moves go through the dedicated ``PATCH /tasks/{id}/status``."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    position: float | None = None


class KanbanBoard(BaseModel):
    todo: list[TaskOut]
    in_progress: list[TaskOut]
    in_review: list[TaskOut]
    done: list[TaskOut]


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    user: UserOut
    created_at: datetime
    updated_at: datetime


class CommentCreate(BaseModel):
    content: str = Field(min_length=1)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1)


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    uploaded_by: uuid.UUID
    original_filename: str
    content_type: str | None
    size_bytes: int
    uploader: UserOut
    created_at: datetime
