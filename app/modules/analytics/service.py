"""Analytics/report business logic."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.repository import AnalyticsRepository
from app.modules.projects.schemas import ProjectOut
from app.modules.tasks.schemas import TaskOut


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)

    async def dashboard(self) -> dict[str, Any]:
        return {
            "total_projects": await self.repo.count_projects(),
            "total_tasks": await self.repo.count_tasks(),
            "total_users": await self.repo.count_users(),
            "projects_by_status": await self.repo.projects_by_status(),
            "tasks_by_status": await self.repo.tasks_by_status(),
            "tasks_by_priority": await self.repo.tasks_by_priority(),
            "overdue_tasks": await self.repo.count_overdue(),
            "recent_projects": [
                ProjectOut.model_validate(p) for p in await self.repo.recent_projects()
            ],
            "recent_tasks": [TaskOut.model_validate(t) for t in await self.repo.recent_tasks()],
            "upcoming_deadlines": [
                TaskOut.model_validate(t) for t in await self.repo.upcoming_deadlines()
            ],
        }

    async def project_analytics(self, project_id: uuid.UUID) -> dict[str, Any]:
        total = await self.repo.count_tasks(project_id)
        done = await self.repo.completed_count(project_id)
        return {
            "project_id": project_id,
            "total_tasks": total,
            "tasks_by_status": await self.repo.tasks_by_status(project_id),
            "tasks_by_priority": await self.repo.tasks_by_priority(project_id),
            "tasks_per_member": await self.repo.tasks_per_member(project_id),
            "completion_percent": round(done / total * 100, 1) if total else 0.0,
            "overdue_tasks": await self.repo.count_overdue(project_id),
        }
