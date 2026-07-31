from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Task, TaskStatus


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, task_id: int) -> Task | None:
        return self.db.scalar(
            select(Task).options(selectinload(Task.assignee)).where(Task.id == task_id)
        )

    def list_for_project(self, project_id: int) -> list[Task]:
        return list(
            self.db.scalars(
                select(Task)
                .options(selectinload(Task.assignee))
                .where(Task.project_id == project_id)
                .order_by(Task.status, Task.position, Task.id)
            )
        )

    def next_position(self, project_id: int, status: TaskStatus) -> float:
        max_pos = self.db.scalar(
            select(func.max(Task.position)).where(
                Task.project_id == project_id, Task.status == status
            )
        )
        return (max_pos or 0.0) + 1000.0

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.flush()
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
