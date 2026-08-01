"""Unit tests: pagination helper against a real (in-memory) database."""

from __future__ import annotations

from app.modules.users.models import User
from app.shared.enums import SortOrder
from app.shared.pagination import PageParams, apply_sort, paginate
from sqlalchemy import select

from tests.conftest import create_user


async def _seed_users(db, count: int) -> None:
    for i in range(count):
        await create_user(db, email=f"user{i:02d}@test.com", password="Passw0rd!x")


async def test_paginate_counts_and_slices(db):
    await _seed_users(db, 25)
    stmt = select(User).order_by(User.email)

    items, meta = await paginate(db, stmt, PageParams(page=1, size=10))
    assert len(items) == 10
    assert meta.total == 25
    assert meta.pages == 3

    items, meta = await paginate(db, stmt, PageParams(page=3, size=10))
    assert len(items) == 5
    assert meta.page == 3


async def test_paginate_empty(db):
    items, meta = await paginate(db, select(User), PageParams(page=1, size=10))
    assert items == []
    assert meta.total == 0
    assert meta.pages == 0


async def test_apply_sort_whitelist(db):
    await _seed_users(db, 3)
    params = PageParams(page=1, size=10, sort="email", order=SortOrder.desc)
    stmt = apply_sort(select(User), params, {"email": User.email}, default=User.created_at)
    items, _ = await paginate(db, stmt, params)
    emails = [u.email for u in items]
    assert emails == sorted(emails, reverse=True)


async def test_apply_sort_unknown_key_falls_back(db):
    await _seed_users(db, 2)
    params = PageParams(page=1, size=10, sort="hashed_password; DROP TABLE users")
    stmt = apply_sort(select(User), params, {"email": User.email}, default=User.email)
    items, _ = await paginate(db, stmt, params)  # no error, default ordering applied
    assert len(items) == 2
