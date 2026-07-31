from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Project, ProjectMember, Task, TaskStatus, User, UserRole
from app.repositories.project_repository import ProjectRepository
from app.utils.exceptions import ForbiddenError, NotFoundError


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)

    def dashboard(self) -> dict:
        today = date.today()
        projects_by_status = dict(
            self.db.execute(select(Project.status, func.count()).group_by(Project.status)).all()
        )
        tasks_by_status = dict(
            self.db.execute(select(Task.status, func.count()).group_by(Task.status)).all()
        )
        tasks_by_priority = dict(
            self.db.execute(select(Task.priority, func.count()).group_by(Task.priority)).all()
        )
        overdue = self.db.scalar(
            select(func.count()).select_from(Task).where(
                Task.due_date < today, Task.status != TaskStatus.done
            )
        )
        recent_projects = list(
            self.db.scalars(select(Project).order_by(Project.created_at.desc()).limit(5))
        )
        recent_tasks = list(
            self.db.scalars(
                select(Task)
                .options(selectinload(Task.assignee))
                .order_by(Task.created_at.desc())
                .limit(5)
            )
        )
        upcoming = list(
            self.db.scalars(
                select(Task)
                .options(selectinload(Task.assignee))
                .where(Task.due_date >= today, Task.status != TaskStatus.done)
                .order_by(Task.due_date)
                .limit(5)
            )
        )
        return {
            "total_projects": self.db.scalar(select(func.count()).select_from(Project)) or 0,
            "total_tasks": self.db.scalar(select(func.count()).select_from(Task)) or 0,
            "total_users": self.db.scalar(select(func.count()).select_from(User)) or 0,
            "projects_by_status": {k.value: v for k, v in projects_by_status.items()},
            "tasks_by_status": {k.value: v for k, v in tasks_by_status.items()},
            "tasks_by_priority": {k.value: v for k, v in tasks_by_priority.items()},
            "overdue_tasks": overdue or 0,
            "recent_projects": recent_projects,
            "recent_tasks": recent_tasks,
            "upcoming_deadlines": upcoming,
        }

    def project_analytics(self, user: User, project_id: int) -> dict:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        if user.role != UserRole.admin and not self.projects.is_member(project_id, user.id):
            raise ForbiddenError("You are not a member of this project")

        today = date.today()
        tasks_by_status = dict(
            self.db.execute(
                select(Task.status, func.count())
                .where(Task.project_id == project_id)
                .group_by(Task.status)
            ).all()
        )
        tasks_by_priority = dict(
            self.db.execute(
                select(Task.priority, func.count())
                .where(Task.project_id == project_id)
                .group_by(Task.priority)
            ).all()
        )
        per_member = dict(
            self.db.execute(
                select(User.full_name, func.count(Task.id))
                .join(Task, Task.assignee_id == User.id)
                .where(Task.project_id == project_id)
                .group_by(User.full_name)
            ).all()
        )
        total = sum(tasks_by_status.values())
        done = tasks_by_status.get(TaskStatus.done, 0)
        overdue = self.db.scalar(
            select(func.count()).select_from(Task).where(
                Task.project_id == project_id,
                Task.due_date < today,
                Task.status != TaskStatus.done,
            )
        )
        return {
            "project_id": project_id,
            "total_tasks": total,
            "tasks_by_status": {k.value: v for k, v in tasks_by_status.items()},
            "tasks_by_priority": {k.value: v for k, v in tasks_by_priority.items()},
            "tasks_per_member": per_member,
            "completion_percent": round(done / total * 100, 1) if total else 0.0,
            "overdue_tasks": overdue or 0,
        }
