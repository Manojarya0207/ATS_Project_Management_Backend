"""User business logic."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import enforce_password_policy, hash_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserRoleUpdate, UserUpdate
from app.shared.enums import UserRole
from app.shared.pagination import PageParams, PaginationMeta, apply_sort, paginate


class UserService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)

    async def list_users(self, params: PageParams) -> tuple[Sequence[User], PaginationMeta]:
        stmt = self.users.list_query(search=params.search)
        stmt = apply_sort(
            stmt,
            params,
            sortable={
                "email": User.email,
                "full_name": User.full_name,
                "created_at": User.created_at,
                "role": User.role,
            },
            default=User.created_at,
        )
        return await paginate(self.db, stmt, params)

    async def get_user(self, user_id: uuid.UUID, actor: User) -> User:
        if actor.role != UserRole.admin and actor.id != user_id:
            raise ForbiddenError("You can only view your own profile")
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def create_user(self, payload: UserCreate) -> User:
        enforce_password_policy(payload.password, self.settings)
        if await self.users.get_by_email(payload.email) is not None:
            raise ConflictError("Email already registered", code=ErrorCode.duplicate_email)
        user = User(
            email=payload.email,
            hashed_password=await hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
        )
        return await self.users.add(user)

    async def update_user(self, user_id: uuid.UUID, payload: UserUpdate, actor: User) -> User:
        if actor.role != UserRole.admin and actor.id != user_id:
            raise ForbiddenError("You can only update your own profile")
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")

        data = payload.model_dump(exclude_unset=True)
        if "is_active" in data and actor.role != UserRole.admin:
            raise ForbiddenError("Only admins can change account status")
        if (
            "email" in data
            and data["email"] != user.email
            and await self.users.get_by_email(data["email"]) is not None
        ):
            raise ConflictError("Email already registered", code=ErrorCode.duplicate_email)
        for field, value in data.items():
            setattr(user, field, value)
        await self.db.flush()
        await self.db.refresh(user)  # reload server-generated updated_at
        return user

    async def update_role(self, user_id: uuid.UUID, payload: UserRoleUpdate) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        user.role = payload.role
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: uuid.UUID, actor: User) -> None:
        if user_id == actor.id:
            raise ForbiddenError("You cannot delete your own account")
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        await self.users.delete(user)  # soft delete
