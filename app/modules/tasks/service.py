"""Task business logic (kanban ordering, assignment notifications)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.projects.repository import ProjectRepository
from app.modules.tasks.models import Task
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskCreate, TaskStatusUpdate, TaskUpdate
from app.modules.users.models import User
from app.shared.enums import TaskStatus
from app.shared.events import EventBus, TaskAssigned
from app.shared.pagination import PageParams, PaginationMeta, apply_sort, paginate


class TaskService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus
        self.tasks = TaskRepository(db)
        self.projects = ProjectRepository(db)

    async def list_for_project(
        self, project_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[Task], PaginationMeta]:
        stmt = self.tasks.list_for_project_query(project_id, search=params.search)
        stmt = apply_sort(
            stmt,
            params,
            sortable={
                "title": Task.title,
                "priority": Task.priority,
                "due_date": Task.due_date,
                "created_at": Task.created_at,
                "position": Task.position,
            },
            default=Task.status,
        )
        if params.sort is None:
            # Preserve original board ordering: status, then position, then id.
            stmt = stmt.order_by(None).order_by(Task.status, Task.position, Task.id)
        return await paginate(self.db, stmt, params)

    async def kanban_board(self, project_id: uuid.UUID) -> dict[str, list[Task]]:
        tasks = await self.tasks.list_for_project(project_id)
        board: dict[str, list[Task]] = {status.value: [] for status in TaskStatus}
        for task in tasks:
            board[task.status.value].append(task)
        return board

    async def create_task(self, payload: TaskCreate, actor: User) -> Task:
        project = await self.projects.get(payload.project_id)
        if project is None:
            raise NotFoundError("Project not found")
        task = Task(
            **payload.model_dump(),
            position=await self.tasks.next_position(payload.project_id, payload.status),
            created_by=actor.id,
        )
        await self.tasks.add(task)
        if task.assignee_id and task.assignee_id != actor.id:
            await self._notify_assignment(task, project.name, actor)
        loaded = await self.tasks.get(task.id)
        assert loaded is not None
        return loaded

    async def update_task(self, task: Task, payload: TaskUpdate, actor: User) -> Task:
        data = payload.model_dump(exclude_unset=True)
        previous_assignee = task.assignee_id
        for field, value in data.items():
            setattr(task, field, value)
        await self.db.flush()

        new_assignee = task.assignee_id
        if (
            "assignee_id" in data
            and new_assignee is not None
            and new_assignee != previous_assignee
            and new_assignee != actor.id
        ):
            project = await self.projects.get(task.project_id)
            await self._notify_assignment(task, project.name if project else "", actor)
        loaded = await self.tasks.get(task.id)
        assert loaded is not None
        return loaded

    async def update_status(self, task: Task, payload: TaskStatusUpdate) -> Task:
        task.status = payload.status
        task.position = (
            payload.position
            if payload.position is not None
            else await self.tasks.next_position(task.project_id, payload.status)
        )
        await self.db.flush()
        loaded = await self.tasks.get(task.id)
        assert loaded is not None
        return loaded

    async def delete_task(self, task: Task) -> None:
        await self.tasks.delete(task)  # soft delete

    async def _notify_assignment(self, task: Task, project_name: str, actor: User) -> None:
        assert task.assignee_id is not None
        await self.event_bus.publish(
            TaskAssigned(
                task_id=task.id,
                task_title=task.title,
                project_name=project_name,
                assignee_id=task.assignee_id,
                actor_id=actor.id,
            ),
            self.db,
        )
