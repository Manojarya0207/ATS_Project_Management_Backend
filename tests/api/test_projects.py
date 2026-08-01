"""API tests: projects CRUD, membership, scoping."""

from __future__ import annotations

from tests.conftest import unwrap
from tests.factories import make_member, make_project

BASE = "/api/v1/projects"


async def test_create_project_admin_only(client, admin_headers, employee_headers):
    r = await client.post(f"{BASE}/", headers=employee_headers, json={"name": "Nope"})
    assert r.status_code == 403
    r = await client.post(
        f"{BASE}/",
        headers=admin_headers,
        json={"name": "Apollo", "description": "Moonshot", "status": "active"},
    )
    assert r.status_code == 201
    data = unwrap(r)
    assert data["name"] == "Apollo"
    assert data["status"] == "active"


async def test_list_scoped_for_employee(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    visible = await make_project(db, creator=admin_user, name="Visible")
    await make_project(db, creator=admin_user, name="Hidden")
    await make_member(db, project=visible, user=employee_user)

    r = await client.get(f"{BASE}/", headers=admin_headers)
    assert r.json()["meta"]["pagination"]["total"] == 2

    r = await client.get(f"{BASE}/", headers=employee_headers)
    names = [p["name"] for p in unwrap(r)]
    assert names == ["Visible"]


async def test_get_project_detail_includes_members(
    client, db, admin_user, employee_user, admin_headers
):
    project = await make_project(db, creator=admin_user)
    await make_member(db, project=project, user=employee_user)
    r = await client.get(f"{BASE}/{project.id}", headers=admin_headers)
    data = unwrap(r)
    assert len(data["members"]) == 1
    assert data["members"][0]["user"]["email"] == employee_user.email


async def test_non_member_403(client, db, admin_user, employee_headers):
    project = await make_project(db, creator=admin_user)
    r = await client.get(f"{BASE}/{project.id}", headers=employee_headers)
    assert r.status_code == 403


async def test_update_project_partial(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user, name="Before")
    r = await client.patch(f"{BASE}/{project.id}", headers=admin_headers, json={"name": "After"})
    assert r.status_code == 200
    data = unwrap(r)
    assert data["name"] == "After"
    assert data["status"] == "active"  # untouched


async def test_add_member_conflict_and_notification(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    project = await make_project(db, creator=admin_user, name="Notify Me")
    r = await client.post(
        f"{BASE}/{project.id}/members",
        headers=admin_headers,
        json={"user_id": str(employee_user.id), "role": "lead"},
    )
    assert r.status_code == 201
    assert unwrap(r)["role"] == "lead"

    # Duplicate → 409
    r = await client.post(
        f"{BASE}/{project.id}/members",
        headers=admin_headers,
        json={"user_id": str(employee_user.id)},
    )
    assert r.status_code == 409
    assert r.json()["errors"][0]["code"] == "ALREADY_MEMBER"

    # Membership notification created via event bus
    r = await client.get("/api/v1/notifications/", headers=employee_headers)
    assert any("Notify Me" in n["message"] for n in unwrap(r))


async def test_remove_member(client, db, admin_user, employee_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    await make_member(db, project=project, user=employee_user)
    r = await client.delete(
        f"{BASE}/{project.id}/members/{employee_user.id}", headers=admin_headers
    )
    assert r.status_code == 204


async def test_delete_project_soft(client, db, admin_user, admin_headers):
    project = await make_project(db, creator=admin_user)
    assert (await client.delete(f"{BASE}/{project.id}", headers=admin_headers)).status_code == 204
    assert (await client.get(f"{BASE}/{project.id}", headers=admin_headers)).status_code == 404
