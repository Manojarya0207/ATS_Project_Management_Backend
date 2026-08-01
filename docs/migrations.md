# Migration Guide

Migrations are managed with Alembic; the environment (`alembic/env.py`) runs
sync or async depending on the URL driver and always sources the URL from
application settings (`DATABASE_URL`) — never from `alembic.ini`.

## Daily workflow

```bash
# 1. Edit models in app/modules/<feature>/models.py
# 2. Autogenerate a revision
alembic revision --autogenerate -m "add archived flag to tasks"
# 3. REVIEW the generated file — autogenerate is a draft, not a decision
# 4. Apply
alembic upgrade head
```

Review checklist for generated revisions:

- [ ] Enum columns render `native_enum=False` (portability).
- [ ] UUID columns render `sa.Uuid()`.
- [ ] Partial indexes carry both `postgresql_where` and `sqlite_where`.
- [ ] `downgrade()` actually reverses the change.
- [ ] Data migrations (backfills) are explicit and batched — autogenerate never
      writes those for you.

## Useful commands

| | |
|---|---|
| Current revision | `alembic current` |
| History | `alembic history --verbose` |
| Upgrade | `alembic upgrade head` (or `+1`, or a revision id) |
| Downgrade | `alembic downgrade -1` (or `base`) |
| Target another DB | `alembic -x db_url=postgresql+psycopg://… upgrade head` |

The `-x db_url=...` override is what CI uses to validate the migration chain
against throwaway SQLite and Postgres databases (upgrade → downgrade → upgrade).

## Startup behaviour

By default the app runs `alembic upgrade head` during startup
(`RUN_MIGRATIONS_ON_STARTUP=true`) — convenient for a single instance. For
multi-replica deployments disable it and run migrations as a release
step/Job so exactly one process migrates.

## Baseline note (v2 rewrite)

The v2 redesign replaced the original integer-PK schema with a single fresh
baseline (`alembic/versions/0001_baseline.py`). There is intentionally **no
data-migration path from v1** — v1 existed only in development. If a v1
database must be preserved, write a one-off ETL that maps `int` ids to new
UUIDs before pointing v2 at it.

## Rules

- Never edit an applied migration; add a new one.
- One logical change per revision, imperative message ("add X", "index Y").
- Test both directions locally before pushing (`upgrade head` + `downgrade -1`).
- Schema-only by default; large backfills belong in batched maintenance
  scripts, not in a deploy-blocking migration.
