"""Notification repository."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, update

from app.core.database import BaseRepository
from app.modules.notifications.models import Notification


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def list_for_user_query(
        self, user_id: uuid.UUID, *, unread_only: bool = False
    ) -> Select[tuple[Notification]]:
        stmt = self._query().where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        return stmt.order_by(Notification.created_at.desc())

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self.db.flush()
