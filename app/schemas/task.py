from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import TaskPriority, TaskStatus
from app.schemas.user import UserOut


class TaskCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    assignee_id: int | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    due_date: date | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    position: float | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: int | None
    assignee: UserOut | None
    due_date: date | None
    position: float
    created_by: int
    created_at: datetime
    updated_at: datetime


class KanbanBoard(BaseModel):
    todo: list[TaskOut]
    in_progress: list[TaskOut]
    in_review: list[TaskOut]
    done: list[TaskOut]
