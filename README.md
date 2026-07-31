# ATS Project Management — Backend

Enterprise Project Management REST API built with **FastAPI + PostgreSQL**. Serves the
[`ATS_Project_Management`](https://github.com/Manojarya0207/ATS_Project_Management) Flutter client.

## Stack

- **FastAPI** (Python 3.12) · **SQLAlchemy 2.0** (typed `Mapped` models) · **Alembic** migrations
- **PostgreSQL 16** · **Pydantic v2**
- **JWT auth** — 30-min access tokens + 7-day rotating refresh tokens, bcrypt hashing
- **RBAC** — `admin` / `employee`, enforced in the service layer (row-level scoping for employees)
- File uploads on local disk behind an S3-ready `FileStorage` abstraction
- Swagger UI auto-generated at `/api/v1/docs`

## Architecture

```
app/
  api/v1/         Route handlers — thin, delegate to services
  services/       Business logic + authorization/scoping rules
  repositories/   All DB queries
  models/         SQLAlchemy ORM models (8 entities)
  schemas/        Pydantic request/response models
  auth/           JWT issue/decode, bcrypt, get_current_user / require_admin deps
  core/           Env-driven settings
  database/       Engine, session factory, declarative base
  utils/          App exception types → HTTP mapping
alembic/          Migrations
scripts/          seed_admin.py, verify_e2e.py
```

## Quick start (local)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt "pydantic[email]"
cp .env.example .env       # set DATABASE_URL + JWT_SECRET_KEY
createdb ats_pm
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed_admin.py        # admin@ats.com / Admin@12345 (override via args)
.venv/bin/uvicorn app.main:app --reload
```

Docs: http://localhost:8000/api/v1/docs

## Quick start (Docker)

```bash
docker compose up --build
```

Brings up Postgres 16 + the API (migrations run on start). Seed the admin with:

```bash
docker compose exec api python scripts/seed_admin.py
```

## API surface

| Module | Endpoints |
|---|---|
| Auth | `POST /auth/register` (always employee) · `/login` · `/refresh` (rotates) · `/logout` · `GET /me` · `POST /change-password` |
| Users (admin) | `GET/POST /users/` · `GET/PATCH/DELETE /users/{id}` · `PATCH /users/{id}/role` |
| Projects | `GET/POST /projects/` · `GET/PATCH/DELETE /projects/{id}` · `POST /projects/{id}/members` · `DELETE /projects/{id}/members/{user_id}` |
| Tasks | `GET /tasks/project/{id}` · `GET /tasks/project/{id}/kanban` · `POST /tasks/` · `GET/PATCH/DELETE /tasks/{id}` · `PATCH /tasks/{id}/status` |
| Comments | `GET/POST /tasks/{id}/comments` · `PATCH/DELETE /comments/{id}` |
| Files | `GET/POST /tasks/{id}/files` · `GET /files/{id}/download` |
| Notifications | `GET /notifications/` · `PATCH /notifications/{id}/read` · `POST /notifications/read-all` |
| Reports | `GET /reports/dashboard` (admin) · `GET /analytics/projects/{id}` |

All routes are under `/api/v1`.

## RBAC rules

- Employees see only projects they are members of; task/comment/file access is scoped through membership
- Admin-only: user management, project create/update/delete, membership management, org dashboard
- Task assignment auto-creates a notification for the assignee
- Password change revokes all outstanding refresh tokens

## Verification

With the API running locally:

```bash
.venv/bin/python scripts/verify_e2e.py
```

Covers login, refresh rotation + revocation, RBAC blocks (401/403), employee scoping,
project/member lifecycle, task + auto-notification, kanban transitions, comments,
file upload/download round-trip, reports/analytics, and change-password — 33 checks.
