"""Reusable pagination, sorting, filtering, and searching.

Usage in a router::

    params: PageParams = Depends()

Usage in a service/repository::

    items, meta = await paginate(db, stmt, params)

The page metadata is returned to clients under ``meta.pagination`` in the
standard response envelope. Offset pagination is the default; the time-ordered
UUIDv7 primary keys keep the door open for cursor pagination (``WHERE id > :cursor``)
on hot lists without a schema change.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.shared.enums import SortOrder


@dataclass(frozen=True)
class PaginationMeta:
    page: int
    size: int
    total: int
    pages: int

    def as_meta(self) -> dict[str, Any]:
        return {
            "pagination": {
                "page": self.page,
                "size": self.size,
                "total": self.total,
                "pages": self.pages,
            }
        }


class PageParams:
    """Common query parameters for list endpoints (page/size/sort/order/search)."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
        sort: str | None = Query(None, description="Field to sort by"),
        order: SortOrder = Query(SortOrder.asc, description="Sort direction"),
        search: str | None = Query(None, min_length=1, max_length=255, description="Search term"),
    ) -> None:
        self.page = page
        self.size = size
        self.sort = sort
        self.order = order
        self.search = search

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def apply_sort(
    stmt: Select[Any],
    params: PageParams,
    sortable: dict[str, Any],
    default: Any,
) -> Select[Any]:
    """Apply whitelisted sorting. ``sortable`` maps public field names to columns;
    unknown sort keys silently fall back to ``default`` (never raw user input)."""
    column = sortable.get(params.sort or "", default)
    ordered = column.desc() if params.order == SortOrder.desc else column.asc()
    return stmt.order_by(ordered)


async def paginate(
    db: AsyncSession,
    stmt: Select[Any],
    params: PageParams,
) -> tuple[Sequence[Any], PaginationMeta]:
    """Execute ``stmt`` with count + offset/limit, returning items and metadata."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    result = await db.execute(stmt.offset(params.offset).limit(params.size))
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total else 0
    return items, PaginationMeta(page=params.page, size=params.size, total=total, pages=pages)
