"""Authentication business logic: registration, login, token rotation with
reuse detection, logout, and password change."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    enforce_password_policy,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import ChangePassword, UserRegister
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.utils import utcnow, uuid7

logger = logging.getLogger("app.auth")


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)

    # --- registration / login -------------------------------------------------

    async def register(self, payload: UserRegister) -> User:
        enforce_password_policy(payload.password, self.settings)
        if await self.users.get_by_email(payload.email) is not None:
            raise ConflictError("Email already registered", code=ErrorCode.duplicate_email)
        # Public registration always creates a regular employee; only admins
        # can create privileged accounts (via the users module).
        user = User(
            email=payload.email,
            hashed_password=await hash_password(payload.password),
            full_name=payload.full_name,
        )
        return await self.users.add(user)

    async def login(self, email: str, password: str) -> tuple[str, str, User]:
        user = await self.users.get_by_email(email)
        if user is None or not await verify_password(password, user.hashed_password):
            raise UnauthorizedError(
                "Incorrect email or password", code=ErrorCode.invalid_credentials
            )
        if not user.is_active:
            raise UnauthorizedError("Account is inactive", code=ErrorCode.inactive_account)
        access, refresh = await self._issue_pair(user, family_id=uuid7())
        return access, refresh, user

    # --- rotation with reuse detection ---------------------------------------

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        record = await self.tokens.get_by_hash(hash_refresh_token(refresh_token))
        if record is None:
            raise UnauthorizedError("Invalid refresh token", code=ErrorCode.invalid_token)

        if record.revoked:
            # A rotated token is being replayed: assume theft and revoke the
            # whole chain so neither party keeps a valid session.
            logger.warning(
                "Refresh token reuse detected for user %s (family %s) — revoking family",
                record.user_id,
                record.family_id,
            )
            await self.tokens.revoke_family(record.family_id)
            # The request will fail with 401 and the session normally rolls
            # back on error — commit now so the security revocation sticks.
            await self.db.commit()
            raise UnauthorizedError(
                "Refresh token reuse detected; all sessions revoked",
                code=ErrorCode.token_reuse_detected,
            )
        if not self.tokens.is_valid(record):
            raise UnauthorizedError("Refresh token expired", code=ErrorCode.invalid_token)

        user = await self.users.get(record.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Account is inactive", code=ErrorCode.inactive_account)

        access, new_refresh = await self._issue_pair(user, family_id=record.family_id)
        new_record = await self.tokens.get_by_hash(hash_refresh_token(new_refresh))
        await self.tokens.revoke(record, replaced_by=new_record.id if new_record else None)
        return access, new_refresh

    async def logout(self, refresh_token: str) -> None:
        record = await self.tokens.get_by_hash(hash_refresh_token(refresh_token))
        if record is not None and not record.revoked:
            await self.tokens.revoke(record)

    async def change_password(self, user: User, payload: ChangePassword) -> None:
        if not await verify_password(payload.current_password, user.hashed_password):
            raise UnauthorizedError(
                "Current password is incorrect", code=ErrorCode.invalid_credentials
            )
        enforce_password_policy(payload.new_password, self.settings)
        user.hashed_password = await hash_password(payload.new_password)
        await self.tokens.revoke_all_for_user(user.id)
        await self.db.flush()

    # --- internal -------------------------------------------------------------

    async def _issue_pair(self, user: User, *, family_id: uuid.UUID) -> tuple[str, str]:
        access = create_access_token(user.id, user.role.value, self.settings)
        refresh = generate_refresh_token()
        await self.tokens.add(
            RefreshToken(
                token_hash=hash_refresh_token(refresh),
                user_id=user.id,
                family_id=family_id,
                expires_at=utcnow() + timedelta(days=self.settings.refresh_token_expire_days),
            )
        )
        return access, refresh
