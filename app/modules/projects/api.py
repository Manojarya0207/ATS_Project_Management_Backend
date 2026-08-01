"""Project API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from app.core.permissions import require_admin
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.projects.dependencies import ProjectServiceDep
from app.modules.projects.permissions import require_project_view
from app.modules.projects.schemas import (
    MemberAdd,
    MemberOut,
    ProjectCreate,
    ProjectDetailOut,
    ProjectOut,
    ProjectUpdate,
)
from app.shared.pagination import PageParams
from app.shared.responses import ApiResponse, ok

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=ApiResponse[list[ProjectOut]])
async def list_projects(
    actor: CurrentUserDep, service: ProjectServiceDep, params: PageParams = Depends()
) -> dict[str, Any]:
    projects, meta = await service.list_projects(actor, params)
    return ok([ProjectOut.model_validate(p) for p in projects], meta=meta.as_meta())


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ProjectOut],
    dependencies=[Depends(require_admin)],
)
async def create_project(
    payload: ProjectCreate, actor: CurrentUserDep, service: ProjectServiceDep
) -> dict[str, Any]:
    project = await service.create_project(payload, actor)
    return ok(ProjectOut.model_validate(project), message="Project created")


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectDetailOut],
    dependencies=[Depends(require_project_view)],
)
async def get_project(project_id: uuid.UUID, service: ProjectServiceDep) -> dict[str, Any]:
    project = await service.get_project_detail(project_id)
    return ok(ProjectDetailOut.model_validate(project))


@router.patch(
    "/{project_id}",
    response_model=ApiResponse[ProjectDetailOut],
    dependencies=[Depends(require_admin)],
)
async def update_project(
    project_id: uuid.UUID, payload: ProjectUpdate, service: ProjectServiceDep
) -> dict[str, Any]:
    project = await service.update_project(project_id, payload)
    return ok(ProjectDetailOut.model_validate(project), message="Project updated")


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_project(project_id: uuid.UUID, service: ProjectServiceDep) -> None:
    await service.delete_project(project_id)


@router.post(
    "/{project_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[MemberOut],
    dependencies=[Depends(require_admin)],
)
async def add_member(
    project_id: uuid.UUID, payload: MemberAdd, actor: CurrentUserDep, service: ProjectServiceDep
) -> dict[str, Any]:
    member = await service.add_member(project_id, payload, actor)
    return ok(MemberOut.model_validate(member), message="Member added")


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def remove_member(
    project_id: uuid.UUID, user_id: uuid.UUID, service: ProjectServiceDep
) -> None:
    await service.remove_member(project_id, user_id)
