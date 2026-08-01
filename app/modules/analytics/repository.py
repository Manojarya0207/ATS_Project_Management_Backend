"""Analytics read-model repository.

Aggregations run in the database (GROUP BY / COUNT) rather than by loading
rows into Python, so response time stays flat as row counts grow.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.projects.models import Project, ProjectMember
from app.modules.tasks.models import Task
from app.modules.users.models import User
from app.shared.enums import ProjectStatus, TaskPriority, TaskStatus


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _scalar(self, stmt: Select[Any]) -> int:
        return int((await self.db.execute(stmt)).scalar_one())

    # --- dashboard-wide counts -------------------------------------------------

    async def count_projects(self) -> int:
        return await self._scalar(
            select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        )

    async def count_tasks(self, project_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count(Task.id)).where(Task.deleted_at.is_(None))
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        return await self._scalar(stmt)

    async def count_users(self) -> int:
        return await self._scalar(select(func.count(User.id)).where(User.deleted_at.is_(None)))

    async def projects_by_status(self) -> dict[str, int]:
        rows = (
            await self.db.execute(
                select(Project.status, func.count(Project.id))
                .where(Project.deleted_at.is_(None))
                .group_by(Project.status)
            )
        ).all()
        counts = dict.fromkeys((s.value for s in ProjectStatus), 0)
        counts.update({status.value: int(n) for status, n in rows})
        return counts

    async def tasks_by_status(self, project_id: uuid.UUID | None = None) -> dict[str, int]:
        stmt = (
            select(Task.status, func.count(Task.id))
            .where(Task.deleted_at.is_(None))
            .group_by(Task.status)
        )
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        rows = (await self.db.execute(stmt)).all()
        counts = dict.fromkeys((s.value for s in TaskStatus), 0)
        counts.update({status.value: int(n) for status, n in rows})
        return counts

    async def tasks_by_priority(self, project_id: uuid.UUID | None = None) -> dict[str, int]:
        stmt = (
            select(Task.priority, func.count(Task.id))
            .where(Task.deleted_at.is_(None))
            .group_by(Task.priority)
        )
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        rows = (await self.db.execute(stmt)).all()
        counts = dict.fromkeys((p.value for p in TaskPriority), 0)
        counts.update({priority.value: int(n) for priority, n in rows})
        return counts

    async def count_overdue(self, project_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count(Task.id)).where(
            Task.deleted_at.is_(None),
            Task.due_date.is_not(None),
            Task.due_date < date.today(),
            Task.status != TaskStatus.done,
        )
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        return await self._scalar(stmt)

    # --- dashboard lists ---------------------------------------------------------

    async def recent_projects(self, limit: int = 5) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def recent_tasks(self, limit: int = 5) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.deleted_at.is_(None))
            .options(selectinload(Task.assignee))
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def upcoming_deadlines(self, limit: int = 5) -> list[Task]:
        stmt = (
            select(Task)
            .where(
                Task.deleted_at.is_(None),
                Task.due_date.is_not(None),
                Task.due_date >= date.today(),
                Task.status != TaskStatus.done,
            )
            .options(selectinload(Task.assignee))
            .order_by(Task.due_date.asc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # --- per-project -------------------------------------------------------------

    async def tasks_per_member(self, project_id: uuid.UUID) -> dict[str, int]:
        """Assigned-task counts keyed by member full name (v1 contract)."""
        rows = (
            await self.db.execute(
                select(User.full_name, func.count(Task.id))
                .join(Task, Task.assignee_id == User.id)
                .where(Task.project_id == project_id, Task.deleted_at.is_(None))
                .group_by(User.id, User.full_name)
            )
        ).all()
        return {full_name: int(n) for full_name, n in rows}

    async def completed_count(self, project_id: uuid.UUID) -> int:
        return await self._scalar(
            select(func.count(Task.id)).where(
                Task.project_id == project_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.done,
            )
        )

    async def member_count(self, project_id: uuid.UUID) -> int:
        return await self._scalar(
            select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project_id)
        )
