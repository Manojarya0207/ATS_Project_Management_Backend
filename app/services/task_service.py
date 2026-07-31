from sqlalchemy.orm import Session

from app.models import Notification, Task, TaskStatus, User, UserRole
from app.repositories.misc_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskStatusUpdate, TaskUpdate
from app.utils.exceptions import ForbiddenError, NotFoundError


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)
        self.projects = ProjectRepository(db)
        self.notifications = NotificationRepository(db)

    def list_for_project(self, user: User, project_id: int) -> list[Task]:
        self._require_project_access(user, project_id)
        return self.tasks.list_for_project(project_id)

    def kanban_board(self, user: User, project_id: int) -> dict[str, list[Task]]:
        tasks = self.list_for_project(user, project_id)
        board: dict[str, list[Task]] = {s.value: [] for s in TaskStatus}
        for task in tasks:
            board[task.status.value].append(task)
        return board

    def get_task(self, user: User, task_id: int) -> Task:
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        self._require_project_access(user, task.project_id)
        return task

    def create_task(self, user: User, data: TaskCreate) -> Task:
        project = self.projects.get(data.project_id)
        if project is None:
            raise NotFoundError("Project not found")
        self._require_project_access(user, data.project_id)
        task = Task(
            **data.model_dump(),
            position=self.tasks.next_position(data.project_id, data.status),
            created_by=user.id,
        )
        self.tasks.create(task)
        if task.assignee_id and task.assignee_id != user.id:
            self._notify_assignment(task, project.name)
        return self.tasks.get(task.id)

    def update_task(self, user: User, task_id: int, data: TaskUpdate) -> Task:
        task = self.get_task(user, task_id)
        old_assignee = task.assignee_id
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        self.db.flush()
        if task.assignee_id and task.assignee_id != old_assignee and task.assignee_id != user.id:
            self._notify_assignment(task, task.project.name)
        return self.tasks.get(task_id)

    def update_status(self, user: User, task_id: int, data: TaskStatusUpdate) -> Task:
        task = self.get_task(user, task_id)
        task.status = data.status
        task.position = (
            data.position
            if data.position is not None
            else self.tasks.next_position(task.project_id, data.status)
        )
        self.db.flush()
        return self.tasks.get(task_id)

    def delete_task(self, user: User, task_id: int) -> None:
        task = self.get_task(user, task_id)
        self.tasks.delete(task)

    def _notify_assignment(self, task: Task, project_name: str) -> None:
        self.notifications.create(
            Notification(
                user_id=task.assignee_id,
                title="New task assigned",
                message=f'You have been assigned "{task.title}" in project "{project_name}".',
            )
        )

    def _require_project_access(self, user: User, project_id: int) -> None:
        if user.role == UserRole.admin:
            return
        if not self.projects.is_member(project_id, user.id):
            raise ForbiddenError("You are not a member of this project")
