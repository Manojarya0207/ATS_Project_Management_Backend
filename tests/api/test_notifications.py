"""API tests: notifications."""

from __future__ import annotations

from tests.conftest import unwrap
from tests.factories import make_project

BASE = "/api/v1/notifications"


async def _seed_notification(client, db, admin_user, employee_user, admin_headers) -> None:
    project = await make_project(db, creator=admin_user, name="Seeded")
    r = await client.post(
        f"/api/v1/projects/{project.id}/members",
        headers=admin_headers,
        json={"user_id": str(employee_user.id)},
    )
    assert r.status_code == 201


async def test_list_own_notifications_only(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    await _seed_notification(client, db, admin_user, employee_user, admin_headers)

    r = await client.get(f"{BASE}/", headers=employee_headers)
    notifications = unwrap(r)
    assert len(notifications) == 1
    assert notifications[0]["is_read"] is False
    assert "user_id" not in notifications[0]  # v1 contract: user_id not exposed

    r = await client.get(f"{BASE}/", headers=admin_headers)
    assert unwrap(r) == []


async def test_mark_read_owner_only(
    client, db, admin_user, employee_user, admin_headers, employee_headers
):
    await _seed_notification(client, db, admin_user, employee_user, admin_headers)
    r = await client.get(f"{BASE}/", headers=employee_headers)
    notification_id = unwrap(r)[0]["id"]

    r = await client.patch(f"{BASE}/{notification_id}/read", headers=admin_headers)
    assert r.status_code == 403

    r = await client.patch(f"{BASE}/{notification_id}/read", headers=employee_headers)
    assert r.status_code == 200
    assert unwrap(r)["is_read"] is True


async def test_read_all(client, db, admin_user, employee_user, admin_headers, employee_headers):
    await _seed_notification(client, db, admin_user, employee_user, admin_headers)
    assert (await client.post(f"{BASE}/read-all", headers=employee_headers)).status_code == 204
    r = await client.get(f"{BASE}/", headers=employee_headers)
    assert all(n["is_read"] for n in unwrap(r))
