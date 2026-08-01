"""Task module dependencies: access-checked task loading shared by task,
comment, and file routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.dependencies import DbDep, EventBusDep, SettingsDep, StorageDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.projects.repository import ProjectRepository
from app.modules.tasks.comment_service import CommentService
from app.modules.tasks.file_service import FileService
from app.modules.tasks.models import Task
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.service import TaskService
from app.shared.enums import UserRole


async def get_accessible_task(task_id: uuid.UUID, user: CurrentUserDep, db: DbDep) -> Task:
    """Load a task and enforce project-scoped access (admin or member)."""
    task = await TaskRepository(db).get(task_id)
    if task is None:
        raise NotFoundError("Task not found")
    if user.role != UserRole.admin and not await ProjectRepository(db).is_member(
        task.project_id, user.id
    ):
        raise ForbiddenError("You are not a member of this project")
    return task


def get_task_service(db: DbDep, event_bus: EventBusDep) -> TaskService:
    return TaskService(db, event_bus)


def get_comment_service(db: DbDep) -> CommentService:
    return CommentService(db)


def get_file_service(db: DbDep, storage: StorageDep, settings: SettingsDep) -> FileService:
    return FileService(db, storage, settings)


AccessibleTaskDep = Annotated[Task, Depends(get_accessible_task)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
FileServiceDep = Annotated[FileService, Depends(get_file_service)]
