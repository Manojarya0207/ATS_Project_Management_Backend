"""End-to-end verification against a running local API (http://localhost:8000)."""
import sys

import httpx

BASE = "http://localhost:8000/api/v1"
ok_count = 0


def check(name: str, cond: bool, extra: str = ""):
    global ok_count
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {extra}")
    if not cond:
        sys.exit(1)
    ok_count += 1


c = httpx.Client(timeout=15)

# --- Admin login ---
r = c.post(f"{BASE}/auth/login", data={"username": "admin@ats.com", "password": "Admin@12345"})
check("admin login", r.status_code == 200)
admin_tokens = r.json()
admin_h = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
check("admin role in login payload", admin_tokens["user"]["role"] == "admin")

# --- Refresh rotation ---
r = c.post(f"{BASE}/auth/refresh", json={"refresh_token": admin_tokens["refresh_token"]})
check("refresh returns new pair", r.status_code == 200)
new_refresh = r.json()["refresh_token"]
r = c.post(f"{BASE}/auth/refresh", json={"refresh_token": admin_tokens["refresh_token"]})
check("old refresh token revoked", r.status_code == 401)

# --- Unauthenticated blocked ---
r = c.get(f"{BASE}/projects/")
check("unauthenticated 401", r.status_code == 401)

# --- Create employee ---
import time
emp_email = f"emp{int(time.time())}@ats.com"
r = c.post(
    f"{BASE}/users/",
    headers=admin_h,
    json={"email": emp_email, "password": "Employee@123", "full_name": "Test Employee"},
)
check("admin creates employee", r.status_code == 201, f"({emp_email})")
emp_id = r.json()["id"]

r = c.post(f"{BASE}/auth/login", data={"username": emp_email, "password": "Employee@123"})
check("employee login", r.status_code == 200)
emp_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

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
    json={"name": "Verification Project", "description": "E2E", "status": "active",
          "start_date": "2026-07-01", "end_date": "2026-12-31"},
)
check("admin creates project", r.status_code == 201)
project_id = r.json()["id"]

# Employee not yet a member — scoped out
r = c.get(f"{BASE}/projects/", headers=emp_h)
check("employee project list scoped (empty of new project)",
      all(p["id"] != project_id for p in r.json()))
r = c.get(f"{BASE}/projects/{project_id}", headers=emp_h)
check("employee blocked from non-member project (403)", r.status_code == 403)

r = c.post(f"{BASE}/projects/{project_id}/members", headers=admin_h,
           json={"user_id": emp_id, "role": "contributor"})
check("admin adds member", r.status_code == 201)

r = c.get(f"{BASE}/projects/", headers=emp_h)
check("employee now sees project", any(p["id"] == project_id for p in r.json()))

# --- Task + auto-notification ---
r = c.post(
    f"{BASE}/tasks/",
    headers=admin_h,
    json={"project_id": project_id, "title": "Verify kanban", "priority": "high",
          "assignee_id": emp_id, "due_date": "2026-08-15"},
)
check("admin creates task w/ assignee", r.status_code == 201)
task_id = r.json()["id"]

r = c.get(f"{BASE}/notifications/", headers=emp_h)
notifs = r.json()
check("assignee auto-notified", any("Verify kanban" in n["message"] for n in notifs))

# --- Kanban ---
r = c.get(f"{BASE}/tasks/project/{project_id}/kanban", headers=emp_h)
check("kanban board grouped", r.status_code == 200 and any(t["id"] == task_id for t in r.json()["todo"]))

r = c.patch(f"{BASE}/tasks/{task_id}/status", headers=emp_h, json={"status": "in_progress"})
check("employee moves task (kanban transition)", r.status_code == 200 and r.json()["status"] == "in_progress")

r = c.get(f"{BASE}/tasks/project/{project_id}/kanban", headers=emp_h)
board = r.json()
check("task moved column", any(t["id"] == task_id for t in board["in_progress"]) and not board["todo"])

# --- Comments ---
r = c.post(f"{BASE}/tasks/{task_id}/comments", headers=emp_h, json={"content": "Working on it"})
check("employee comments", r.status_code == 201)
r = c.get(f"{BASE}/tasks/{task_id}/comments", headers=admin_h)
check("comment visible", any(cm["content"] == "Working on it" for cm in r.json()))

# --- Files ---
r = c.post(f"{BASE}/tasks/{task_id}/files", headers=emp_h,
           files={"file": ("hello.txt", b"hello world", "text/plain")})
check("file upload", r.status_code == 201)
file_id = r.json()["id"]
r = c.get(f"{BASE}/files/{file_id}/download", headers=admin_h)
check("file download round-trip", r.status_code == 200 and r.content == b"hello world")

# --- Notifications read ---
if notifs:
    r = c.patch(f"{BASE}/notifications/{notifs[0]['id']}/read", headers=emp_h)
    check("mark notification read", r.status_code == 200 and r.json()["is_read"])
r = c.post(f"{BASE}/notifications/read-all", headers=emp_h)
check("read-all", r.status_code == 204)

# --- Reports & analytics ---
r = c.get(f"{BASE}/reports/dashboard", headers=admin_h)
check("admin dashboard report", r.status_code == 200 and r.json()["total_projects"] >= 1)
r = c.get(f"{BASE}/analytics/projects/{project_id}", headers=emp_h)
check("project analytics (member access)", r.status_code == 200 and r.json()["total_tasks"] == 1)

# --- Profile / change password ---
r = c.get(f"{BASE}/auth/me", headers=emp_h)
check("GET /me", r.status_code == 200 and r.json()["email"] == emp_email)
r = c.post(f"{BASE}/auth/change-password", headers=emp_h,
           json={"current_password": "Employee@123", "new_password": "Employee@456"})
check("change password", r.status_code == 204)
r = c.post(f"{BASE}/auth/login", data={"username": emp_email, "password": "Employee@456"})
check("login with new password", r.status_code == 200)

# --- Cleanup: delete verification project (cascades tasks/comments/files) ---
r = c.delete(f"{BASE}/projects/{project_id}", headers=admin_h)
check("admin deletes project", r.status_code == 204)
r = c.delete(f"{BASE}/users/{emp_id}", headers=admin_h)
check("admin deletes user", r.status_code == 204)

print(f"\nAll {ok_count} checks passed.")
