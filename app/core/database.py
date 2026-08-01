"""Database foundation: declarative base, naming conventions, reusable mixins,
engine/sessionmaker factory, and the generic repository base.

Design notes:
- ``MetaData`` naming conventions make every constraint/index name deterministic,
  which keeps Alembic autogenerate diffs stable across databases.
- ``sa.Uuid`` maps to native ``UUID`` on PostgreSQL and ``CHAR(32)`` on SQLite,
  so no custom type decorator is needed.
- The sessionmaker uses ``expire_on_commit=False`` because the request-scoped
  session commits *before* the response is serialized; expired attributes would
  otherwise trigger lazy async refreshes outside the greenlet context.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import DateTime, MetaData, Select, Uuid, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import Settings
from app.shared.utils import utcnow, uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# --- Reusable mixins ---------------------------------------------------------


class UUIDPkMixin:
    """Time-ordered UUIDv7 primary key (index-friendly, globally unique)."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Rows are hidden, not destroyed. Repositories filter these out by default."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# --- Engine / session factory ------------------------------------------------


def build_engine(settings: Settings) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create the async engine + sessionmaker from settings.

    Called once from the application lifespan (and from tests/scripts); the
    result is stored on ``app.state`` — never at module level.
    """
    url = settings.database_url
    kwargs: dict[str, Any] = {"echo": settings.database_echo, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["max_overflow"] = settings.database_max_overflow

    engine = create_async_engine(url, **kwargs)
    sessionmaker = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)
    return engine, sessionmaker


# --- Generic repository ------------------------------------------------------

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Data-access base: session + model bound, soft-delete aware.

    Repositories contain *only* persistence concerns. They flush (to obtain
    server defaults / surface constraint errors early) but never commit — the
    request-scoped session commits on success in ``get_db``.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _query(self, *, include_deleted: bool = False) -> Select[tuple[ModelT]]:
        stmt = select(self.model)
        if not include_deleted and issubclass(self.model, SoftDeleteMixin):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        stmt = self._query().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Soft-delete when the model supports it; hard-delete otherwise."""
        if isinstance(entity, SoftDeleteMixin):
            entity.deleted_at = utcnow()
            await self.db.flush()
        else:
            await self.db.delete(entity)
            await self.db.flush()

    async def hard_delete(self, entity: ModelT) -> None:
        await self.db.delete(entity)
        await self.db.flush()

    async def list_all(self, stmt: Select[tuple[ModelT]] | None = None) -> Sequence[ModelT]:
        result = await self.db.execute(stmt if stmt is not None else self._query())
        return result.scalars().all()
