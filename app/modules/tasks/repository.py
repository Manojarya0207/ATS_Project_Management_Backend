"""Task, comment, and file repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from app.core.constants import POSITION_STEP
from app.core.database import BaseRepository
from app.modules.tasks.models import Comment, FileAttachment, Task
from app.shared.enums import TaskStatus


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get(self, entity_id: uuid.UUID) -> Task | None:
        stmt = self._query().where(Task.id == entity_id).options(selectinload(Task.assignee))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list_for_project_query(
        self, project_id: uuid.UUID, *, search: str | None = None
    ) -> Select[tuple[Task]]:
        stmt = (
            self._query().where(Task.project_id == project_id).options(selectinload(Task.assignee))
        )
        if search:
            stmt = stmt.where(Task.title.ilike(f"%{search}%"))
        return stmt

    async def list_for_project(self, project_id: uuid.UUID) -> list[Task]:
        stmt = self.list_for_project_query(project_id).order_by(Task.status, Task.position, Task.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def next_position(self, project_id: uuid.UUID, status: TaskStatus) -> float:
        stmt = select(func.max(Task.position)).where(
            Task.project_id == project_id,
            Task.status == status,
            Task.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        current_max = result.scalar_one_or_none()
        return (current_max or 0.0) + POSITION_STEP


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def get(self, entity_id: uuid.UUID) -> Comment | None:
        stmt = self._query().where(Comment.id == entity_id).options(selectinload(Comment.user))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list_for_task_query(self, task_id: uuid.UUID) -> Select[tuple[Comment]]:
        return (
            self._query()
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.user))
            .order_by(Comment.created_at.asc())
        )


class FileRepository(BaseRepository[FileAttachment]):
    model = FileAttachment

    async def get(self, entity_id: uuid.UUID) -> FileAttachment | None:
        stmt = (
            self._query()
            .where(FileAttachment.id == entity_id)
            .options(selectinload(FileAttachment.uploader))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_task(self, task_id: uuid.UUID) -> list[FileAttachment]:
        stmt = (
            self._query()
            .where(FileAttachment.task_id == task_id)
            .options(selectinload(FileAttachment.uploader))
            .order_by(FileAttachment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
