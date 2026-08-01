"""End-to-end verification against a running local API (http://localhost:8000).

v2: all JSON responses use the standard envelope {success, message, data, meta,
errors}; IDs are UUID strings; list endpoints are paginated (data + meta.pagination).
"""

from __future__ import annotations

import sys
import time

import httpx

BASE = "http://localhost:8000/api/v1"
ok_count = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global ok_count
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {extra}")
    if not cond:
        sys.exit(1)
    ok_count += 1


def data(r: httpx.Response):
    body = r.json()
    assert body.get("success") is True, f"expected success envelope, got: {body}"
    return body["data"]


def err_code(r: httpx.Response) -> str:
    errors = r.json().get("errors") or []
    return errors[0]["code"] if errors else ""


c = httpx.Client(timeout=15)

# --- Health & readiness ---
r = c.get("http://localhost:8000/health")
check("health", r.status_code == 200 and data(r)["status"] == "ok")
r = c.get("http://localhost:8000/health/ready")
check("readiness (db ping)", r.status_code == 200)
check("secure headers present", r.headers.get("X-Content-Type-Options") == "nosniff")
check("request id header present", bool(r.headers.get("X-Request-ID")))

# --- Admin login ---
r = c.post(f"{BASE}/auth/login", data={"username": "admin@ats.com", "password": "Admin@12345"})
check("admin login", r.status_code == 200)
body = r.json()
check("login: top-level access_token (Swagger compat)", bool(body.get("access_token")))
admin_data = data(r)
admin_h = {"Authorization": f"Bearer {admin_data['access_token']}"}
check("admin role in login payload", admin_data["user"]["role"] == "admin")

# --- Refresh rotation + family reuse detection ---
r = c.post(f"{BASE}/auth/refresh", json={"refresh_token": admin_data["refresh_token"]})
check("refresh returns new pair", r.status_code == 200)
second_refresh = data(r)["refresh_token"]
r = c.post(f"{BASE}/auth/refresh", json={"refresh_token": admin_data["refresh_token"]})
check("old refresh token revoked (reuse detected)", r.status_code == 401)
check("reuse error code", err_code(r) == "TOKEN_REUSE_DETECTED")
r = c.post(f"{BASE}/auth/refresh", json={"refresh_token": second_refresh})
check("family revoked after reuse (successor dead too)", r.status_code == 401)

# Re-login since the whole admin session family was revoked.
r = c.post(f"{BASE}/auth/login", data={"username": "admin@ats.com", "password": "Admin@12345"})
check("admin re-login", r.status_code == 200)
admin_data = data(r)
admin_h = {"Authorization": f"Bearer {admin_data['access_token']}"}

# --- Unauthenticated blocked ---
r = c.get(f"{BASE}/projects/")
check("unauthenticated 401", r.status_code == 401 and r.json()["success"] is False)

# --- Create employee ---
emp_email = f"emp{int(time.time())}@ats.com"
r = c.post(
    f"{BASE}/users/",
    headers=admin_h,
    json={"email": emp_email, "password": "Employee@123", "full_name": "Test Employee"},
)
check("admin creates employee", r.status_code == 201, f"({emp_email})")
emp_id = data(r)["id"]

# --- Password policy enforced ---
r = c.post(
    f"{BASE}/users/",
    headers=admin_h,
    json={
        "email": f"weak{int(time.time())}@ats.com",
        "password": "alllowercase1",
        "full_name": "Weak",
    },
)
check("weak password rejected (policy)", r.status_code == 422 and err_code(r) == "WEAK_PASSWORD")

r = c.post(f"{BASE}/auth/login", data={"username": emp_email, "password": "Employee@123"})
check("employee login", r.status_code == 200)
emp_h = {"Authorization": f"Bearer {data(r)['access_token']}"}

# --- RBAC: employee blocked from admin routes ---
r = c.get(f"{BASE}/users/", headers=emp_h)
check("employee blocked from user list (403)", r.status_code == 403)
r = c.get(f"{BASE}/reports/dashboard", headers=emp_h)
check("employee blocked from dashboard report (403)", r.status_code == 403)
r = c.post(f"{BASE}/projects/", headers=emp_h, json={"name": "Nope"})
check("employee blocked from project create (403)", r.status_code == 403)

# --- Project lifecycle ---
r = c.post(
    f"{BASE}/projects/",
    headers=admin_h,
    json={
        "name": "Verification Project",
        "description": "E2E",
        "status": "active",
        "start_date": "2026-07-01",
        "end_date": "2026-12-31",
    },
)
check("admin creates project", r.status_code == 201)
project_id = data(r)["id"]

# Pagination meta present on lists
r = c.get(f"{BASE}/projects/", headers=admin_h)
meta = r.json()["meta"]
check("project list paginated", "pagination" in meta and meta["pagination"]["total"] >= 1)

# Employee not yet a member — scoped out
r = c.get(f"{BASE}/projects/", headers=emp_h)
check(
    "employee project list scoped (empty of new project)",
    all(p["id"] != project_id for p in data(r)),
)
r = c.get(f"{BASE}/projects/{project_id}", headers=emp_h)
check("employee blocked from non-member project (403)", r.status_code == 403)

r = c.post(
    f"{BASE}/projects/{project_id}/members",
    headers=admin_h,
    json={"user_id": emp_id, "role": "contributor"},
)
check("admin adds member", r.status_code == 201)
r = c.post(
    f"{BASE}/projects/{project_id}/members",
    headers=admin_h,
    json={"user_id": emp_id, "role": "contributor"},
)
check("duplicate member 409", r.status_code == 409 and err_code(r) == "ALREADY_MEMBER")

r = c.get(f"{BASE}/projects/", headers=emp_h)
check("employee now sees project", any(p["id"] == project_id for p in data(r)))

# --- Task + auto-notification ---
r = c.post(
    f"{BASE}/tasks/",
    headers=admin_h,
    json={
        "project_id": project_id,
        "title": "Verify kanban",
        "priority": "high",
        "assignee_id": emp_id,
        "due_date": "2026-08-15",
    },
)
check("admin creates task w/ assignee", r.status_code == 201)
task_id = data(r)["id"]

r = c.get(f"{BASE}/notifications/", headers=emp_h)
notifs = data(r)
check("assignee auto-notified", any("Verify kanban" in n["message"] for n in notifs))

# --- Kanban ---
r = c.get(f"{BASE}/tasks/project/{project_id}/kanban", headers=emp_h)
check(
    "kanban board grouped",
    r.status_code == 200 and any(t["id"] == task_id for t in data(r)["todo"]),
)

r = c.patch(f"{BASE}/tasks/{task_id}/status", headers=emp_h, json={"status": "in_progress"})
check(
    "employee moves task (kanban transition)",
    r.status_code == 200 and data(r)["status"] == "in_progress",
)

r = c.get(f"{BASE}/tasks/project/{project_id}/kanban", headers=emp_h)
board = data(r)
check(
    "task moved column", any(t["id"] == task_id for t in board["in_progress"]) and not board["todo"]
)

# --- Optimistic locking surfaces version ---
r = c.get(f"{BASE}/tasks/{task_id}", headers=emp_h)
check("task exposes version", isinstance(data(r).get("version"), int))

# --- Comments ---
r = c.post(f"{BASE}/tasks/{task_id}/comments", headers=emp_h, json={"content": "Working on it"})
check("employee comments", r.status_code == 201)
r = c.get(f"{BASE}/tasks/{task_id}/comments", headers=admin_h)
check("comment visible", any(cm["content"] == "Working on it" for cm in data(r)))

# --- Files ---
r = c.post(
    f"{BASE}/tasks/{task_id}/files",
    headers=emp_h,
    files={"file": ("hello.txt", b"hello world", "text/plain")},
)
check("file upload", r.status_code == 201)
file_id = data(r)["id"]
r = c.get(f"{BASE}/files/{file_id}/download", headers=admin_h)
check(
    "file download round-trip (raw, not enveloped)",
    r.status_code == 200 and r.content == b"hello world",
)

# --- Notifications read ---
if notifs:
    r = c.patch(f"{BASE}/notifications/{notifs[0]['id']}/read", headers=emp_h)
    check("mark notification read", r.status_code == 200 and data(r)["is_read"])
r = c.post(f"{BASE}/notifications/read-all", headers=emp_h)
check("read-all", r.status_code == 204)

# --- Reports & analytics ---
r = c.get(f"{BASE}/reports/dashboard", headers=admin_h)
check("admin dashboard report", r.status_code == 200 and data(r)["total_projects"] >= 1)
r = c.get(f"{BASE}/analytics/projects/{project_id}", headers=emp_h)
check("project analytics (member access)", r.status_code == 200 and data(r)["total_tasks"] == 1)

# --- Profile / change password ---
r = c.get(f"{BASE}/auth/me", headers=emp_h)
check("GET /me", r.status_code == 200 and data(r)["email"] == emp_email)
r = c.post(
    f"{BASE}/auth/change-password",
    headers=emp_h,
    json={"current_password": "Employee@123", "new_password": "Employee@456"},
)
check("change password", r.status_code == 204)
r = c.post(f"{BASE}/auth/login", data={"username": emp_email, "password": "Employee@456"})
check("login with new password", r.status_code == 200)

# --- Cleanup: delete verification project (soft delete) + user ---
r = c.delete(f"{BASE}/projects/{project_id}", headers=admin_h)
check("admin deletes project", r.status_code == 204)
r = c.get(f"{BASE}/projects/{project_id}", headers=admin_h)
check("soft-deleted project hidden", r.status_code == 404)
r = c.delete(f"{BASE}/users/{emp_id}", headers=admin_h)
check("admin deletes user", r.status_code == 204)

print(f"\nAll {ok_count} checks passed.")
