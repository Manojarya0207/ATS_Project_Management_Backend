"""User API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from app.core.permissions import require_admin
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.users.dependencies import UserServiceDep
from app.modules.users.schemas import UserCreate, UserOut, UserRoleUpdate, UserUpdate
from app.shared.pagination import PageParams
from app.shared.responses import ApiResponse, ok

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=ApiResponse[list[UserOut]], dependencies=[Depends(require_admin)])
async def list_users(service: UserServiceDep, params: PageParams = Depends()) -> dict[str, Any]:
    users, meta = await service.list_users(params)
    return ok([UserOut.model_validate(u) for u in users], meta=meta.as_meta())


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserOut],
    dependencies=[Depends(require_admin)],
)
async def create_user(payload: UserCreate, service: UserServiceDep) -> dict[str, Any]:
    user = await service.create_user(payload)
    return ok(UserOut.model_validate(user), message="User created")


@router.get("/{user_id}", response_model=ApiResponse[UserOut])
async def get_user(
    user_id: uuid.UUID, actor: CurrentUserDep, service: UserServiceDep
) -> dict[str, Any]:
    user = await service.get_user(user_id, actor)
    return ok(UserOut.model_validate(user))


@router.patch("/{user_id}", response_model=ApiResponse[UserOut])
async def update_user(
    user_id: uuid.UUID, payload: UserUpdate, actor: CurrentUserDep, service: UserServiceDep
) -> dict[str, Any]:
    user = await service.update_user(user_id, payload, actor)
    return ok(UserOut.model_validate(user), message="User updated")


@router.patch(
    "/{user_id}/role",
    response_model=ApiResponse[UserOut],
    dependencies=[Depends(require_admin)],
)
async def update_role(
    user_id: uuid.UUID, payload: UserRoleUpdate, service: UserServiceDep
) -> dict[str, Any]:
    user = await service.update_role(user_id, payload)
    return ok(UserOut.model_validate(user), message="Role updated")


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_user(user_id: uuid.UUID, actor: CurrentUserDep, service: UserServiceDep) -> None:
    await service.delete_user(user_id, actor)
