"""API tests: tasks, kanban board, status transitions."""

from __future__ import annotations

from tests.conftest import unwrap
from tests.factories import make_member, make_project, make_task

BASE = "/api/v1/tasks"


async def test_member_creates_task(client, db, admin_user, employee_user, employee_headers):
    project = await make_project(db, creator=admin_user)
    await make_member(db, project=project, user=employee_user)
    r = await client.post(
        f"{BASE}/",
        headers=employee_headers,
        json={"project_id": str(project.id), "title": "Member task", "priority": "high"},
    )
    assert r.status_code == 201
    data = unwrap(r)
    assert data["position"] == 1000.0
    assert data["status"] == "todo"
    assert data["version"] == 1


async def test_non_member_cannot_create_task(client, db, admin_user, employee_headers):
    project = await make_project(db, creator=admin_user)
    r = await client.post(
        f"{BASE}/",
        headers=employee_headers,
        json={"project_id": str(project.id), "title": "Nope"},
    )
    assert r.status_code == 403


async def test_assignment_creates_notification(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    project = await make_project(db, creator=admin_user, name="P")
    await make_member(db, project=project, user=employee_user)
    r = await client.post(
        f"{BASE}/",
        headers=admin_headers,
        json={
            "project_id": str(project.id),
            "title": "Assigned work",
            "assignee_id": str(employee_user.id),
        },
    )
    assert r.status_code == 201
    assert unwrap(r)["assignee"]["email"] == employee_user.email

    r = await client.get("/api/v1/notifications/", headers=employee_headers)
    assert any("Assigned work" in n["message"] for n in unwrap(r))


async def test_kanban_board_groups_by_status(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    await make_task(db, project=project, creator=admin_user, title="A", position=1000)
    await make_task(db, project=project, creator=admin_user, title="B", position=2000)

    r = await client.get(f"{BASE}/project/{project.id}/kanban", headers=admin_headers)
    board = unwrap(r)
    assert set(board.keys()) == {"todo", "in_progress", "in_review", "done"}
    assert [t["title"] for t in board["todo"]] == ["A", "B"]
    assert board["done"] == []


async def test_status_transition_moves_column(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    task = await make_task(db, project=project, creator=admin_user)

    r = await client.patch(
        f"{BASE}/{task.id}/status", headers=admin_headers, json={"status": "in_review"}
    )
    assert r.status_code == 200
    assert unwrap(r)["status"] == "in_review"

    r = await client.get(f"{BASE}/project/{project.id}/kanban", headers=admin_headers)
    board = unwrap(r)
    assert board["todo"] == []
    assert len(board["in_review"]) == 1


async def test_update_task_excludes_status(client, db, admin_user, admin_headers):
    """TaskUpdate must not accept status — kanban moves use the /status route."""
    project = await make_project(db, creator=admin_user)
    task = await make_task(db, project=project, creator=admin_user)
    r = await client.patch(
        f"{BASE}/{task.id}",
        headers=admin_headers,
        json={"title": "Renamed", "status": "done"},
    )
    assert r.status_code == 200
    data = unwrap(r)
    assert data["title"] == "Renamed"
    assert data["status"] == "todo"  # extra field ignored


async def test_list_tasks_paginated(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    for i in range(7):
        await make_task(db, project=project, creator=admin_user, title=f"T{i}", position=i * 1000)
    r = await client.get(f"{BASE}/project/{project.id}?page=2&size=5", headers=admin_headers)
    assert len(unwrap(r)) == 2
    assert r.json()["meta"]["pagination"]["total"] == 7


async def test_delete_task_soft(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    task = await make_task(db, project=project, creator=admin_user)
    assert (await client.delete(f"{BASE}/{task.id}", headers=admin_headers)).status_code == 204
    assert (await client.get(f"{BASE}/{task.id}", headers=admin_headers)).status_code == 404
