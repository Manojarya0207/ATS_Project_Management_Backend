"""Auth dependency providers: current-user resolution from a bearer token."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.constants import ErrorCode
from app.core.dependencies import DbDep, SettingsDep
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbDep,
    settings: SettingsDep,
) -> User:
    payload = decode_access_token(token, settings)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token", code=ErrorCode.invalid_token)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid token subject", code=ErrorCode.invalid_token) from None

    user = await UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account not found or inactive", code=ErrorCode.inactive_account)
    return user


def get_auth_service(db: DbDep, settings: SettingsDep) -> AuthService:
    return AuthService(db, settings)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
