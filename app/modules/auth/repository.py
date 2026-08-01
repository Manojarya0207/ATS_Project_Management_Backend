"""Refresh-token repository."""

from __future__ import annotations

import uuid

from sqlalchemy import update

from app.core.database import BaseRepository
from app.modules.auth.models import RefreshToken
from app.shared.utils import utcnow


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = self._query().where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, *, replaced_by: uuid.UUID | None = None) -> None:
        token.revoked = True
        token.replaced_by_id = replaced_by
        await self.db.flush()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.db.flush()

    def is_valid(self, token: RefreshToken) -> bool:
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            # SQLite stores tz-aware datetimes naively; normalize to UTC.
            from datetime import UTC

            expires_at = expires_at.replace(tzinfo=UTC)
        return not token.revoked and expires_at > utcnow()
