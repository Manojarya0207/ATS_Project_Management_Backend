# Database Guide

## Engines

- **Production/staging**: PostgreSQL 16 via `postgresql+asyncpg://`.
- **Local development**: SQLite via `sqlite+aiosqlite:///./ats_pm.db` (default).
- **Tests**: in-memory aiosqlite.

Cross-engine compatibility is deliberate: enums are stored as `VARCHAR(32)`
with CHECK constraints (`native_enum=False`) and UUIDs use `sa.Uuid` (native
`UUID` on PG, `CHAR(32)` on SQLite), so one migration path serves both.

## Entity-relationship diagram

```mermaid
erDiagram
    users ||--o{ refresh_tokens : "has"
    users ||--o{ project_members : "joins"
    users ||--o{ notifications : "receives"
    users ||--o{ comments : "writes"
    projects ||--o{ project_members : "has"
    projects ||--o{ tasks : "contains"
    tasks ||--o{ comments : "has"
    tasks ||--o{ file_attachments : "has"
    users ||--o{ tasks : "assigned (assignee_id)"

    users {
        uuid id PK
        string email "partial-unique on live rows"
        string hashed_password
        string full_name
        enum role "admin | employee"
        bool is_active
        datetime created_at
        datetime updated_at
        datetime deleted_at "soft delete"
    }
    projects {
        uuid id PK
        string name
        text description
        enum status "planning..archived"
        date start_date
        date end_date
        uuid created_by FK "RESTRICT"
        datetime deleted_at "soft delete"
    }
    project_members {
        uuid id PK
        uuid project_id FK "CASCADE"
        uuid user_id FK "CASCADE"
        enum role "lead | contributor"
    }
    tasks {
        uuid id PK
        uuid project_id FK "CASCADE"
        string title
        enum status "todo..done"
        enum priority "low..urgent"
        uuid assignee_id FK "SET NULL"
        date due_date
        float position "kanban ordering"
        uuid created_by FK "RESTRICT"
        int version "optimistic lock"
        datetime deleted_at "soft delete"
    }
    comments {
        uuid id PK
        uuid task_id FK "CASCADE"
        uuid user_id FK "CASCADE"
        text content
        datetime deleted_at "soft delete"
    }
    file_attachments {
        uuid id PK
        uuid task_id FK "CASCADE"
        uuid uploaded_by FK "CASCADE"
        string original_filename
        string stored_filename "unique"
        bigint size_bytes
    }
    notifications {
        uuid id PK
        uuid user_id FK "CASCADE"
        enum type
        string title
        text message
        bool is_read
    }
    refresh_tokens {
        uuid id PK
        string token_hash "sha256, unique"
        uuid user_id FK "CASCADE"
        uuid family_id "rotation chain"
        datetime expires_at
        bool revoked
        uuid replaced_by_id
    }
```

## Conventions

- **Primary keys**: UUIDv7 (time-ordered) generated app-side (`shared/utils.uuid7`).
- **Naming**: all constraints/indexes named via the `MetaData` naming convention
  in `core/database.py` — autogenerate diffs stay deterministic.
- **Timestamps**: `created_at`/`updated_at` on every table (`TimestampMixin`),
  timezone-aware, server defaults.
- **Soft delete**: `deleted_at` on users, projects, tasks, comments
  (`SoftDeleteMixin`). Repositories exclude soft-deleted rows by default;
  `hard_delete()` exists for genuinely disposable rows (refresh tokens).
- **Audit**: `created_by` on projects/tasks (RESTRICT — a user who authored
  records cannot be hard-deleted out from under them); soft delete preserves
  the audit trail.

## Notable indexes

| Index | Purpose |
|---|---|
| `uq_users_email_active` (partial: `deleted_at IS NULL`) | email uniqueness among live accounts; freed on soft delete |
| `ix_tasks_project_status_position` | kanban column fetch: `WHERE project_id AND status ORDER BY position` |
| `ix_notifications_user_read` | unread-badge query |
| `ix_refresh_tokens_token_hash` (unique) | O(1) token lookup on refresh |
| `ix_refresh_tokens_family_id` | family-wide revocation on reuse detection |
| single-column indexes on every FK | joins + cascade performance |

## Concurrency

- **Optimistic locking**: `tasks.version` is a SQLAlchemy `version_id_col`.
  Concurrent writes raise `StaleDataError` → HTTP `409 STALE_VERSION`.
- **Kanban ordering**: `position` floats spaced by 1000; moving between
  midpoints halves the gap. Rebalancing (rewriting positions when gaps
  exhaust) is a straightforward maintenance job if boards ever churn enough
  to need it.
