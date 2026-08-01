"""Analytics schemas — field names preserve the v1 report contract."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.modules.projects.schemas import ProjectOut
from app.modules.tasks.schemas import TaskOut


class DashboardReport(BaseModel):
    total_projects: int
    total_tasks: int
    total_users: int
    projects_by_status: dict[str, int]
    tasks_by_status: dict[str, int]
    tasks_by_priority: dict[str, int]
    overdue_tasks: int
    recent_projects: list[ProjectOut]
    recent_tasks: list[TaskOut]
    upcoming_deadlines: list[TaskOut]


class ProjectAnalytics(BaseModel):
    project_id: uuid.UUID
    total_tasks: int
    tasks_by_status: dict[str, int]
    tasks_by_priority: dict[str, int]
    tasks_per_member: dict[str, int]
    completion_percent: float
    overdue_tasks: int
