"""Unit tests: task service kanban-position logic and event publishing."""

from __future__ import annotations

from app.modules.notifications import handlers
from app.modules.notifications.repository import NotificationRepository
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskCreate, TaskStatusUpdate
from app.modules.tasks.service import TaskService
from app.shared.enums import TaskStatus
from app.shared.events import EventBus

from tests.conftest import create_user
from tests.factories import make_member, make_project, make_task


async def test_next_position_increments_by_step(db):
    admin = await create_user(db, email="a@test.com", password="Passw0rd!x")
    project = await make_project(db, creator=admin)
    repo = TaskRepository(db)

    assert await repo.next_position(project.id, TaskStatus.todo) == 1000.0
    await make_task(db, project=project, creator=admin, position=1000.0)
    assert await repo.next_position(project.id, TaskStatus.todo) == 2000.0


async def test_status_change_appends_to_target_column(db):
    admin = await create_user(db, email="a@test.com", password="Passw0rd!x")
    project = await make_project(db, creator=admin)
    await make_task(
        db, project=project, creator=admin, status=TaskStatus.in_progress, position=5000.0
    )
    task = await make_task(db, project=project, creator=admin, position=1000.0)

    service = TaskService(db, EventBus())
    updated = await service.update_status(task, TaskStatusUpdate(status=TaskStatus.in_progress))
    assert updated.status == TaskStatus.in_progress
    assert updated.position == 6000.0  # max(5000) + step


async def test_status_change_respects_explicit_position(db):
    admin = await create_user(db, email="a@test.com", password="Passw0rd!x")
    project = await make_project(db, creator=admin)
    task = await make_task(db, project=project, creator=admin)

    service = TaskService(db, EventBus())
    updated = await service.update_status(
        task, TaskStatusUpdate(status=TaskStatus.done, position=1500.0)
    )
    assert updated.position == 1500.0


async def test_create_task_notifies_assignee_via_event_bus(db):
    admin = await create_user(db, email="a@test.com", password="Passw0rd!x")
    employee = await create_user(db, email="e@test.com", password="Passw0rd!x")
    project = await make_project(db, creator=admin)
    await make_member(db, project=project, user=employee)

    bus = EventBus()
    handlers.register(bus)
    service = TaskService(db, bus)
    await service.create_task(
        TaskCreate(project_id=project.id, title="Assigned task", assignee_id=employee.id),
        actor=admin,
    )
    await db.commit()

    notifications = await NotificationRepository(db).list_all()
    assert any(n.user_id == employee.id and "Assigned task" in n.message for n in notifications)


async def test_self_assignment_does_not_notify(db):
    admin = await create_user(db, email="a@test.com", password="Passw0rd!x")
    project = await make_project(db, creator=admin)

    bus = EventBus()
    handlers.register(bus)
    service = TaskService(db, bus)
    await service.create_task(
        TaskCreate(project_id=project.id, title="Self task", assignee_id=admin.id),
        actor=admin,
    )
    await db.commit()

    assert await NotificationRepository(db).list_all() == []
