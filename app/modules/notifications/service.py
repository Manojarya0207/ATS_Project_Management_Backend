"""Notification business logic."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository
from app.shared.enums import NotificationType
from app.shared.pagination import PageParams, PaginationMeta, paginate


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)

    async def list_for_user(
        self, user_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[Notification], PaginationMeta]:
        stmt = self.notifications.list_for_user_query(user_id)
        return await paginate(self.db, stmt, params)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = await self.notifications.get(notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        if notification.user_id != user_id:
            raise ForbiddenError("Not your notification")
        notification.is_read = True
        await self.db.flush()
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.notifications.mark_all_read(user_id)

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        type_: NotificationType = NotificationType.general,
    ) -> Notification:
        return await self.notifications.add(
            Notification(user_id=user_id, title=title, message=message, type=type_)
        )
