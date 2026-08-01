# Developer Onboarding

## Prerequisites

- Python 3.12+
- (optional) Docker + Docker Compose for Postgres
- (optional) `make`-style muscle memory — commands below are plain

## First-time setup

```bash
git clone <repo-url> && cd ATS_Project_Management_Backend

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env        # defaults run on SQLite, no DB server needed

alembic upgrade head        # create the schema
python scripts/seed_admin.py   # admin@ats.com / Admin@12345

uvicorn app.main:app --reload
```

Open Swagger: http://localhost:8000/api/v1/docs
(log in via the **Authorize** button with the seeded admin credentials —
`username` is the email).

## Everyday commands

| Task | Command |
|---|---|
| Run the API (reload) | `uvicorn app.main:app --reload` |
| Run tests | `pytest` |
| Lint | `ruff check app tests scripts` |
| Format | `ruff format app tests scripts` |
| Type-check | `mypy app` |
| New migration | `alembic revision --autogenerate -m "describe change"` |
| Apply migrations | `alembic upgrade head` |
| End-to-end smoke test | `python scripts/verify_e2e.py` (against a running server) |
| Full stack via Docker | `docker compose -f docker-compose.dev.yml up` |

## Where things go

- **New endpoint on an existing feature** → the module's `api.py` (controller),
  logic in `service.py`, queries in `repository.py`, DTOs in `schemas.py`.
- **New feature** → new directory under `app/modules/<feature>/` mirroring an
  existing module; register its router in `app/main.py`.
- **New model** → the owning module's `models.py`; it is auto-registered via
  `app/modules/__init__.py`; then `alembic revision --autogenerate`.
- **New setting** → `app/core/config.py` + document it in `.env.example`.
- **New error code** → `app/core/constants.py` (`ErrorCode`).
- **Cross-module side effects** → publish a domain event (`app/shared/events.py`)
  and subscribe in the consuming module's `handlers.py`.

## Conventions

- Controllers stay thin: validate → call service → wrap in `ok(...)`.
- Services own business rules and authorization *decisions*; route-level
  dependencies (`require_admin`, `require_project_view`, `get_accessible_task`)
  own authorization *enforcement* for resource access.
- Repositories never `commit()` — the request commits on success in `get_db`.
- Every relationship that feeds a response must be eager-loaded
  (`selectinload`); relationships are declared `lazy="raise"` so violations
  fail loudly in development rather than silently degrading.
- All datetimes are timezone-aware UTC (`app.shared.utils.utcnow`).
- Type hints everywhere; `mypy app` must stay clean.

## Testing

- `tests/unit/` — services/helpers against an in-memory database.
- `tests/api/` — full HTTP round-trips through the ASGI app (httpx).
- Fixtures live in `tests/conftest.py`; persisted-object builders in
  `tests/factories.py`.
- The suite uses aiosqlite in-memory with `StaticPool` — no external services
  required; CI additionally validates migrations against real Postgres.
