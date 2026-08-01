"""Shared pytest fixtures: app, database, client, auth helpers.

Tests run against an in-memory aiosqlite database (StaticPool keeps the single
connection alive across the whole test), with migrations replaced by
``Base.metadata.create_all`` for speed. A separate test exercises the real
Alembic baseline.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from app.core.config import Environment, Settings
from app.core.database import Base
from app.core.security import hash_password
from app.main import create_app
from app.modules.users.models import User
from app.shared.enums import UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


def make_settings(**overrides) -> Settings:
    defaults: dict = {
        "environment": Environment.testing,
        "database_url": "sqlite+aiosqlite://",
        "jwt_secret_key": "test-secret-key-for-the-test-suite-only",
        "run_migrations_on_startup": False,
        "rate_limit_enabled": False,
        "upload_dir": "uploads-test",
        "log_level": "WARNING",
        "_env_file": None,  # ignore local .env
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
async def app_and_engine():
    settings = make_settings()
    app = create_app(settings)

    engine = create_async_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # The lifespan builds its own engine from settings; for the in-memory test
    # DB we must inject ours (a second engine would see an empty database).
    async with lifespan_ctx(app):
        sessionmaker = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)
        app.state.engine = engine
        app.state.sessionmaker = sessionmaker
        yield app, engine

    await engine.dispose()


@asynccontextmanager
async def lifespan_ctx(app):
    async with app.router.lifespan_context(app):
        yield


@pytest.fixture
async def app_instance(app_and_engine):
    return app_and_engine[0]


@pytest.fixture
async def db(app_and_engine) -> AsyncIterator[AsyncSession]:
    _, engine = app_and_engine
    sessionmaker = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
        await session.commit()


@pytest.fixture
async def client(app_and_engine) -> AsyncIterator[AsyncClient]:
    app, _ = app_and_engine
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# --- User / auth helpers ------------------------------------------------------

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Admin@12345"
EMPLOYEE_EMAIL = "employee@test.com"
EMPLOYEE_PASSWORD = "Employee@123"


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    role: UserRole = UserRole.employee,
    full_name: str = "Test User",
) -> User:
    user = User(
        email=email,
        hashed_password=await hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    return user


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest.fixture
async def admin_user(db) -> User:
    return await create_user(
        db, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, role=UserRole.admin, full_name="Admin"
    )


@pytest.fixture
async def employee_user(db) -> User:
    return await create_user(
        db, email=EMPLOYEE_EMAIL, password=EMPLOYEE_PASSWORD, full_name="Employee"
    )


@pytest.fixture
async def admin_headers(client, admin_user) -> dict[str, str]:
    return await login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
async def employee_headers(client, employee_user) -> dict[str, str]:
    return await login(client, EMPLOYEE_EMAIL, EMPLOYEE_PASSWORD)


def unwrap(response) -> dict | list:
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


def make_uuid() -> str:
    return str(uuid.uuid4())
