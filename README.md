# ATS Project Management — Backend

Enterprise-grade Project Management REST API built with **FastAPI + async SQLAlchemy + PostgreSQL**.
Serves the [`ATS_Project_Management`](https://github.com/Manojarya0207/ATS_Project_Management) Flutter client.

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

## Highlights

- **Fully async** — SQLAlchemy 2.0 `AsyncSession` (asyncpg / aiosqlite), async services and routes; bcrypt offloaded to worker threads
- **Feature-first architecture** — `app/modules/{auth,users,projects,tasks,notifications,analytics}` each with `api / service / repository / schemas / models`; cross-cutting concerns in `core/`, `shared/`, `infrastructure/`
- **UUIDv7 primary keys** — time-ordered (index-friendly), non-enumerable, shard/microservice-safe
- **Standard response envelope** — every endpoint returns `{success, message, data, meta, errors}` with machine-readable error codes
- **Hardened auth** — JWT access tokens + rotating refresh-token *families* with reuse detection (replaying a rotated token revokes the whole chain), tokens hashed at rest, password policy, rate-limited auth endpoints
- **Centralized permission engine** — `require_admin`, `ProjectAccessPolicy`, `get_accessible_task` dependencies; RBAC (`admin`/`employee`) + project-membership scoping
- **Soft deletes, audit fields, optimistic locking** — `deleted_at` everywhere it matters, `created_by` audit, `version` column on tasks (concurrent kanban drags → clean 409)
- **Pluggable infrastructure** — storage (local / S3 / R2 / Azure), cache (memory / Redis), queue (inline / Celery) behind Protocols; switch via env vars, zero business-logic changes
- **Observability** — structured JSON logs with request/correlation IDs, `/health` + `/health/live` + `/health/ready`, Prometheus-ready `/metrics` hook, `X-Process-Time`
- **Quality gates** — 72-test suite (unit + API), ruff, mypy, migration up/down checks on SQLite *and* Postgres, Docker build — all in GitHub Actions

## Documentation

| | |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System design, diagrams, every architectural decision explained |
| [docs/onboarding.md](docs/onboarding.md) | Developer setup + day-to-day workflow + conventions |
| [docs/deployment.md](docs/deployment.md) | Docker/Kubernetes, environments, production checklist |
| [docs/database.md](docs/database.md) | ERD, conventions, indexes, concurrency |
| [docs/migrations.md](docs/migrations.md) | Alembic workflow and rules |

## Quick start (local, SQLite — zero setup)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

alembic upgrade head
python scripts/seed_admin.py          # admin@ats.com / Admin@12345
uvicorn app.main:app --reload
```

Swagger UI: **http://localhost:8000/api/v1/docs** (use the Authorize button; `username` = email).

## Quick start (Docker — Postgres)

```bash
cp .env.example .env                  # set JWT_SECRET_KEY (openssl rand -hex 32)
docker compose up -d --build
docker compose exec api python scripts/seed_admin.py
```

Development stack with reload + exposed Postgres: `docker compose -f docker-compose.dev.yml up`.

## Response contract

```jsonc
// success
{ "success": true, "message": "Task created", "data": { ... },
  "meta": { "pagination": { "page": 1, "size": 20, "total": 57, "pages": 3 } },
  "errors": [] }

// failure
{ "success": false, "message": "Refresh token reuse detected; all sessions revoked",
  "data": null, "meta": null,
  "errors": [ { "code": "TOKEN_REUSE_DETECTED", "detail": "...", "field": null } ] }
```

Exceptions: `204` responses have no body; `GET /files/{id}/download` streams the raw file;
`POST /auth/login` duplicates `access_token` top-level for Swagger's OAuth2 flow.

List endpoints accept `?page=&size=&sort=&order=&search=` (sort keys are whitelisted per endpoint).

## API surface

All routes under `/api/v1`. IDs are UUID strings.

| Module | Endpoints |
|---|---|
| Auth | `POST /auth/register` (always employee) · `/login` (OAuth2 form) · `/refresh` (rotates + reuse detection) · `/logout` · `GET /me` · `POST /change-password` |
| Users (admin) | `GET/POST /users/` · `GET/PATCH/DELETE /users/{id}` · `PATCH /users/{id}/role` |
| Projects | `GET/POST /projects/` · `GET/PATCH/DELETE /projects/{id}` · `POST /projects/{id}/members` · `DELETE /projects/{id}/members/{user_id}` |
| Tasks | `GET /tasks/project/{id}` · `GET /tasks/project/{id}/kanban` · `POST /tasks/` · `GET/PATCH/DELETE /tasks/{id}` · `PATCH /tasks/{id}/status` |
| Comments | `GET/POST /tasks/{id}/comments` · `PATCH/DELETE /comments/{id}` |
| Files | `GET/POST /tasks/{id}/files` · `GET /files/{id}/download` |
| Notifications | `GET /notifications/` · `PATCH /notifications/{id}/read` · `POST /notifications/read-all` |
| Reports | `GET /reports/dashboard` (admin) · `GET /analytics/projects/{id}` |
| Health | `GET /health` · `/health/live` · `/health/ready` |

## RBAC rules

- Employees see only projects they are members of; task/comment/file access is scoped through membership (enforced by route-level policy dependencies)
- Admin-only: user management, project create/update/delete, membership management, org dashboard
- `ProjectMember.role` (`lead`/`contributor`) is modeled and enforceable via `require_project_lead`
- Task assignment and project membership auto-create notifications (via the in-process domain event bus)
- Password change and refresh-token reuse revoke outstanding sessions

## Development

```bash
pytest                      # 72 unit + API tests (in-memory DB, no services needed)
ruff check app tests scripts
ruff format app tests scripts
mypy app
python scripts/verify_e2e.py   # 46-check E2E against a running server
```

CI (GitHub Actions) runs lint, format-check, mypy, pytest, migration
upgrade/downgrade against SQLite + Postgres, and the Docker build on every push/PR.

## Project layout

```
app/
├── main.py            create_app() factory + lifespan DI wiring
├── core/              config, database base/mixins, security, logging,
│                      middleware, exceptions, permissions, rate limiting
├── shared/            envelope, pagination, enums, event bus, utils
├── infrastructure/    storage / cache / queue backends + health/metrics
└── modules/           auth, users, projects, tasks (+comments/files),
                       notifications, analytics — feature-first
alembic/               async env.py + single baseline migration
scripts/               seed_admin.py, verify_e2e.py
tests/                 conftest, factories, unit/, api/
docs/                  architecture, onboarding, deployment, database, migrations
```

## v2 breaking changes (from v1)

- All JSON bodies now use the envelope; payloads moved under `data`, errors from `{"detail"}` to `errors[]` with codes
- IDs are UUIDv7 strings (previously integers); fresh migration baseline
- List endpoints are paginated (default 20/page, max 100)
- Refresh tokens are hashed at rest; reuse revokes the token family
- Route paths, methods, field names, and status codes are unchanged
