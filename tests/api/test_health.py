"""API tests: health endpoints, envelope shape, middleware headers."""

from __future__ import annotations


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


async def test_liveness(client):
    r = await client.get("/health/live")
    assert r.status_code == 200


async def test_readiness_checks_database(client):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["data"]["checks"]["database"] == "ok"


async def test_request_id_and_secure_headers(client):
    r = await client.get("/health")
    assert r.headers.get("X-Request-ID")
    assert r.headers.get("X-Correlation-ID")
    assert r.headers.get("X-Process-Time")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


async def test_correlation_id_propagates(client):
    r = await client.get("/health", headers={"X-Correlation-ID": "upstream-trace-42"})
    assert r.headers["X-Correlation-ID"] == "upstream-trace-42"


async def test_validation_error_envelope(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "x", "full_name": ""},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None
    assert all(e["code"] == "VALIDATION_ERROR" for e in body["errors"])
    fields = {e["field"] for e in body["errors"]}
    assert "email" in fields


async def test_404_route_returns_json(client):
    r = await client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
