"""Event-bus subscribers that turn domain events into notifications.

Registered during application startup (:func:`register`); handlers reuse the
publisher's session so the notification row commits atomically with the change
that triggered it.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.service import NotificationService
from app.shared.enums import NotificationType
from app.shared.events import DomainEvent, EventBus, MemberAddedToProject, TaskAssigned


async def on_member_added(event: DomainEvent, db: AsyncSession) -> None:
    assert isinstance(event, MemberAddedToProject)
    await NotificationService(db).create(
        user_id=event.user_id,
        title="Added to project",
        message=f'You have been added to project "{event.project_name}".',
        type_=NotificationType.project_membership,
    )


async def on_task_assigned(event: DomainEvent, db: AsyncSession) -> None:
    assert isinstance(event, TaskAssigned)
    await NotificationService(db).create(
        user_id=event.assignee_id,
        title="New task assigned",
        message=f'You have been assigned "{event.task_title}" in project "{event.project_name}".',
        type_=NotificationType.task_assignment,
    )


def register(bus: EventBus) -> None:
    bus.subscribe(MemberAddedToProject, on_member_added)
    bus.subscribe(TaskAssigned, on_task_assigned)
