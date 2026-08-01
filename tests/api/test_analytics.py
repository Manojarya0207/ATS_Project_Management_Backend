"""API tests: dashboard report and project analytics."""

from __future__ import annotations

from datetime import date, timedelta

from app.shared.enums import TaskStatus

from tests.conftest import unwrap
from tests.factories import make_member, make_project, make_task


async def test_dashboard_admin_only(client, admin_headers, employee_headers):
    assert (
        await client.get("/api/v1/reports/dashboard", headers=employee_headers)
    ).status_code == 403
    r = await client.get("/api/v1/reports/dashboard", headers=admin_headers)
    assert r.status_code == 200


async def test_dashboard_aggregates(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    await make_task(db, project=project, creator=admin_user, status=TaskStatus.done)
    await make_task(
        db,
        project=project,
        creator=admin_user,
        title="Overdue",
        due_date=date.today() - timedelta(days=3),
    )

    r = await client.get("/api/v1/reports/dashboard", headers=admin_headers)
    data = unwrap(r)
    assert data["total_projects"] == 1
    assert data["total_tasks"] == 2
    assert data["tasks_by_status"]["done"] == 1
    assert data["overdue_tasks"] == 1
    assert len(data["recent_projects"]) == 1
    assert data["projects_by_status"]["active"] == 1


async def test_project_analytics_member_access(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    project = await make_project(db, creator=admin_user)
    await make_member(db, project=project, user=employee_user)
    await make_task(
        db,
        project=project,
        creator=admin_user,
        status=TaskStatus.done,
        assignee_id=employee_user.id,
    )
    await make_task(db, project=project, creator=admin_user, title="Open")

    r = await client.get(f"/api/v1/analytics/projects/{project.id}", headers=employee_headers)
    assert r.status_code == 200
    data = unwrap(r)
    assert data["total_tasks"] == 2
    assert data["completion_percent"] == 50.0
    assert data["tasks_per_member"] == {employee_user.full_name: 1}


async def test_project_analytics_non_member_403(client, db, admin_user, employee_headers):
    project = await make_project(db, creator=admin_user)
    r = await client.get(f"/api/v1/analytics/projects/{project.id}", headers=employee_headers)
    assert r.status_code == 403
