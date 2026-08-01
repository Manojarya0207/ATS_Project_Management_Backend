"""User repository — persistence only, no business logic."""

from __future__ import annotations

from sqlalchemy import Select, or_

from app.core.database import BaseRepository
from app.modules.users.models import User


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = self._query().where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list_query(self, search: str | None = None) -> Select[tuple[User]]:
        stmt = self._query()
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
        return stmt
