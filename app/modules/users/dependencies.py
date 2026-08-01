"""User module dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import DbDep, SettingsDep
from app.modules.users.service import UserService


def get_user_service(db: DbDep, settings: SettingsDep) -> UserService:
    return UserService(db, settings)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
