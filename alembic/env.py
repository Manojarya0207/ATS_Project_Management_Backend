"""Alembic environment — supports both sync (CLI with a sync driver URL) and
async (app-configured ``+asyncpg``/``+aiosqlite`` URLs) execution.

The database URL always comes from application settings / DATABASE_URL — never
from ``alembic.ini``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

import app.modules  # noqa: F401 — registers all models on Base.metadata
from app.core.config import Settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    # -x db_url=... override (used by CI to point at a throwaway database)
    x_args = context.get_x_argument(as_dictionary=True)
    return x_args.get("db_url") or Settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async(url: str) -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
        await connection.commit()
    await engine.dispose()


def run_migrations_online() -> None:
    url = _database_url()
    if "+asyncpg" in url or "+aiosqlite" in url:
        asyncio.run(_run_async(url))
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            _run_migrations(connection)
            connection.commit()
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
