"""API tests: user management + RBAC."""

from __future__ import annotations

from tests.conftest import unwrap

BASE = "/api/v1/users"


async def test_list_users_admin_only(client, admin_headers, employee_headers):
    r = await client.get(f"{BASE}/", headers=employee_headers)
    assert r.status_code == 403
    r = await client.get(f"{BASE}/", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["meta"]["pagination"]["total"] == 2


async def test_list_users_pagination_and_search(client, admin_headers):
    for i in range(5):
        await client.post(
            f"{BASE}/",
            headers=admin_headers,
            json={
                "email": f"search{i}@test.com",
                "password": "Str0ngPass1",
                "full_name": f"Search Target {i}",
            },
        )
    r = await client.get(f"{BASE}/?page=1&size=3", headers=admin_headers)
    assert len(unwrap(r)) == 3
    r = await client.get(f"{BASE}/?search=Search+Target", headers=admin_headers)
    assert r.json()["meta"]["pagination"]["total"] == 5


async def test_admin_creates_user_with_role(client, admin_headers):
    r = await client.post(
        f"{BASE}/",
        headers=admin_headers,
        json={
            "email": "second-admin@test.com",
            "password": "Str0ngPass1",
            "full_name": "Second Admin",
            "role": "admin",
        },
    )
    assert r.status_code == 201
    assert unwrap(r)["role"] == "admin"


async def test_employee_reads_only_self(client, admin_user, employee_user, employee_headers):
    r = await client.get(f"{BASE}/{employee_user.id}", headers=employee_headers)
    assert r.status_code == 200
    r = await client.get(f"{BASE}/{admin_user.id}", headers=employee_headers)
    assert r.status_code == 403


async def test_employee_cannot_change_is_active(client, employee_user, employee_headers):
    r = await client.patch(
        f"{BASE}/{employee_user.id}", headers=employee_headers, json={"is_active": False}
    )
    assert r.status_code == 403


async def test_role_update_admin_only(client, employee_user, admin_headers, employee_headers):
    r = await client.patch(
        f"{BASE}/{employee_user.id}/role", headers=employee_headers, json={"role": "admin"}
    )
    assert r.status_code == 403
    r = await client.patch(
        f"{BASE}/{employee_user.id}/role", headers=admin_headers, json={"role": "admin"}
    )
    assert r.status_code == 200
    assert unwrap(r)["role"] == "admin"


async def test_admin_cannot_delete_self(client, admin_user, admin_headers):
    r = await client.delete(f"{BASE}/{admin_user.id}", headers=admin_headers)
    assert r.status_code == 403


async def test_delete_user_is_soft(client, employee_user, admin_headers):
    r = await client.delete(f"{BASE}/{employee_user.id}", headers=admin_headers)
    assert r.status_code == 204
    r = await client.get(f"{BASE}/{employee_user.id}", headers=admin_headers)
    assert r.status_code == 404  # hidden by soft-delete filter
