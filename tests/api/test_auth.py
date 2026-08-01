"""API tests: auth flows (register, login, refresh rotation + reuse detection,
logout, change-password)."""

from __future__ import annotations

from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    unwrap,
)

BASE = "/api/v1/auth"


async def test_register_creates_employee(client):
    r = await client.post(
        f"{BASE}/register",
        json={"email": "new@test.com", "password": "Str0ngPass!", "full_name": "New User"},
    )
    assert r.status_code == 201
    data = unwrap(r)
    assert data["email"] == "new@test.com"
    assert data["role"] == "employee"  # public registration never grants admin
    assert "hashed_password" not in data


async def test_register_duplicate_email_409(client):
    payload = {"email": "dup@test.com", "password": "Str0ngPass1", "full_name": "Dup"}
    assert (await client.post(f"{BASE}/register", json=payload)).status_code == 201
    r = await client.post(f"{BASE}/register", json=payload)
    assert r.status_code == 409
    assert r.json()["errors"][0]["code"] == "DUPLICATE_EMAIL"


async def test_register_weak_password_422(client):
    r = await client.post(
        f"{BASE}/register",
        json={"email": "weak@test.com", "password": "alllowercase", "full_name": "Weak"},
    )
    assert r.status_code == 422
    assert r.json()["errors"][0]["code"] == "WEAK_PASSWORD"


async def test_login_success_envelope_and_swagger_compat(client, admin_user):
    r = await client.post(
        f"{BASE}/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["access_token"]  # top-level duplicate for Swagger Authorize
    data = body["data"]
    assert data["access_token"] and data["refresh_token"]
    assert data["user"]["email"] == ADMIN_EMAIL


async def test_login_wrong_password_401(client, admin_user):
    r = await client.post(f"{BASE}/login", data={"username": ADMIN_EMAIL, "password": "nope"})
    assert r.status_code == 401
    assert r.json()["success"] is False
    assert r.headers.get("WWW-Authenticate") == "Bearer"


async def test_refresh_rotation_and_reuse_detection(client, admin_user):
    r = await client.post(
        f"{BASE}/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    first = unwrap(r)["refresh_token"]

    r = await client.post(f"{BASE}/refresh", json={"refresh_token": first})
    assert r.status_code == 200
    second = unwrap(r)["refresh_token"]
    assert second != first

    # Replaying the rotated token trips reuse detection...
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": first})
    assert r.status_code == 401
    assert r.json()["errors"][0]["code"] == "TOKEN_REUSE_DETECTED"

    # ...and revokes the entire family, killing the successor too.
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": second})
    assert r.status_code == 401


async def test_logout_revokes_refresh_token(client, admin_user):
    r = await client.post(
        f"{BASE}/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    refresh = unwrap(r)["refresh_token"]
    assert (await client.post(f"{BASE}/logout", json={"refresh_token": refresh})).status_code == 204
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


async def test_me_requires_auth(client):
    assert (await client.get(f"{BASE}/me")).status_code == 401


async def test_change_password_revokes_sessions(client, admin_user, admin_headers):
    r = await client.post(
        f"{BASE}/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    refresh = unwrap(r)["refresh_token"]

    r = await client.post(
        f"{BASE}/change-password",
        headers=admin_headers,
        json={"current_password": ADMIN_PASSWORD, "new_password": "NewAdmin@999"},
    )
    assert r.status_code == 204

    # Old refresh tokens are dead; new password works.
    assert (
        await client.post(f"{BASE}/refresh", json={"refresh_token": refresh})
    ).status_code == 401
    r = await client.post(
        f"{BASE}/login", data={"username": ADMIN_EMAIL, "password": "NewAdmin@999"}
    )
    assert r.status_code == 200
