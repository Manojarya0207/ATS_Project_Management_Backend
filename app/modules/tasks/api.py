"""Task API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from app.core.exceptions import ForbiddenError
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.projects.permissions import require_project_view
from app.modules.tasks.dependencies import AccessibleTaskDep, TaskServiceDep
from app.modules.tasks.schemas import (
    KanbanBoard,
    TaskCreate,
    TaskOut,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.shared.enums import UserRole
from app.shared.pagination import PageParams
from app.shared.responses import ApiResponse, ok

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get(
    "/project/{project_id}",
    response_model=ApiResponse[list[TaskOut]],
    dependencies=[Depends(require_project_view)],
)
async def list_project_tasks(
    project_id: uuid.UUID, service: TaskServiceDep, params: PageParams = Depends()
) -> dict[str, Any]:
    tasks, meta = await service.list_for_project(project_id, params)
    return ok([TaskOut.model_validate(t) for t in tasks], meta=meta.as_meta())


@router.get(
    "/project/{project_id}/kanban",
    response_model=ApiResponse[KanbanBoard],
    dependencies=[Depends(require_project_view)],
)
async def kanban_board(project_id: uuid.UUID, service: TaskServiceDep) -> dict[str, Any]:
    board = await service.kanban_board(project_id)
    return ok(
        {column: [TaskOut.model_validate(t) for t in tasks] for column, tasks in board.items()}
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TaskOut])
async def create_task(
    payload: TaskCreate, actor: CurrentUserDep, service: TaskServiceDep
) -> dict[str, Any]:
    # Access is enforced against the payload's project (any member or admin
    # may create tasks — matching v1 behaviour).
    if actor.role != UserRole.admin and not await service.projects.is_member(
        payload.project_id, actor.id
    ):
        raise ForbiddenError("You are not a member of this project")
    task = await service.create_task(payload, actor)
    return ok(TaskOut.model_validate(task), message="Task created")


@router.get("/{task_id}", response_model=ApiResponse[TaskOut])
async def get_task(task: AccessibleTaskDep) -> dict[str, Any]:
    return ok(TaskOut.model_validate(task))


@router.patch("/{task_id}", response_model=ApiResponse[TaskOut])
async def update_task(
    payload: TaskUpdate, task: AccessibleTaskDep, actor: CurrentUserDep, service: TaskServiceDep
) -> dict[str, Any]:
    updated = await service.update_task(task, payload, actor)
    return ok(TaskOut.model_validate(updated), message="Task updated")


@router.patch("/{task_id}/status", response_model=ApiResponse[TaskOut])
async def update_task_status(
    payload: TaskStatusUpdate, task: AccessibleTaskDep, service: TaskServiceDep
) -> dict[str, Any]:
    updated = await service.update_status(task, payload)
    return ok(TaskOut.model_validate(updated), message="Task status updated")


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task: AccessibleTaskDep, service: TaskServiceDep) -> None:
    await service.delete_task(task)
