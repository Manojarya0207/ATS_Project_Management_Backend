"""Comment API routes.

Mixed nesting preserved from v1: list/create under ``/tasks/{task_id}/comments``,
update/delete under ``/comments/{comment_id}``.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import DbDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.tasks.dependencies import (
    AccessibleTaskDep,
    CommentServiceDep,
    get_accessible_task,
)
from app.modules.tasks.schemas import CommentCreate, CommentOut, CommentUpdate
from app.shared.pagination import PageParams
from app.shared.responses import ApiResponse, ok

router = APIRouter(tags=["Comments"])


@router.get("/tasks/{task_id}/comments", response_model=ApiResponse[list[CommentOut]])
async def list_comments(
    task: AccessibleTaskDep, service: CommentServiceDep, params: PageParams = Depends()
) -> dict[str, Any]:
    comments, meta = await service.list_for_task(task.id, params)
    return ok([CommentOut.model_validate(c) for c in comments], meta=meta.as_meta())


@router.post(
    "/tasks/{task_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[CommentOut],
)
async def create_comment(
    payload: CommentCreate,
    task: AccessibleTaskDep,
    actor: CurrentUserDep,
    service: CommentServiceDep,
) -> dict[str, Any]:
    comment = await service.create(task.id, payload, actor)
    return ok(CommentOut.model_validate(comment), message="Comment added")


@router.patch("/comments/{comment_id}", response_model=ApiResponse[CommentOut])
async def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdate,
    actor: CurrentUserDep,
    service: CommentServiceDep,
    db: DbDep,
) -> dict[str, Any]:
    comment = await service.get(comment_id)
    await get_accessible_task(comment.task_id, actor, db)  # project access check
    updated = await service.update(comment_id, payload, actor)
    return ok(CommentOut.model_validate(updated), message="Comment updated")


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID, actor: CurrentUserDep, service: CommentServiceDep, db: DbDep
) -> None:
    comment = await service.get(comment_id)
    await get_accessible_task(comment.task_id, actor, db)  # project access check
    await service.delete(comment_id, actor)
