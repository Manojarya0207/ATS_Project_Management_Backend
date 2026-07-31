from pydantic import BaseModel

from app.schemas.project import ProjectOut
from app.schemas.task import TaskOut


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
    project_id: int
    total_tasks: int
    tasks_by_status: dict[str, int]
    tasks_by_priority: dict[str, int]
    tasks_per_member: dict[str, int]
    completion_percent: float
    overdue_tasks: int
