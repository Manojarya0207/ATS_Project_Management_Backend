"""Notification API routes."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import DbDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.notifications.schemas import NotificationOut
from app.modules.notifications.service import NotificationService
from app.shared.pagination import PageParams
from app.shared.responses import ApiResponse, ok

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(db: DbDep) -> NotificationService:
    return NotificationService(db)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("/", response_model=ApiResponse[list[NotificationOut]])
async def list_notifications(
    user: CurrentUserDep, service: NotificationServiceDep, params: PageParams = Depends()
) -> dict[str, Any]:
    notifications, meta = await service.list_for_user(user.id, params)
    return ok([NotificationOut.model_validate(n) for n in notifications], meta=meta.as_meta())


@router.patch("/{notification_id}/read", response_model=ApiResponse[NotificationOut])
async def mark_read(
    notification_id: uuid.UUID, user: CurrentUserDep, service: NotificationServiceDep
) -> dict[str, Any]:
    notification = await service.mark_read(notification_id, user.id)
    return ok(NotificationOut.model_validate(notification), message="Notification read")


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(user: CurrentUserDep, service: NotificationServiceDep) -> None:
    await service.mark_all_read(user.id)
