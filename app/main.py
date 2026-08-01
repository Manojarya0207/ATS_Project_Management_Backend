"""Application entrypoint — ``create_app`` factory and lifespan wiring.

All shared resources (settings, engine, storage, cache, queue, event bus) are
constructed during startup and stored on ``app.state``; dependency providers in
``app.core.dependencies`` resolve them per-request. Nothing lives at module
level, so tests and scripts can build isolated app instances.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core import ratelimit
from app.core.config import Settings
from app.core.database import build_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import (
    RequestContextMiddleware,
    RequestLoggingMiddleware,
    SecureHeadersMiddleware,
)
from app.infrastructure.cache import get_cache
from app.infrastructure.monitoring.health import router as health_router
from app.infrastructure.monitoring.metrics import instrument
from app.infrastructure.queue import get_queue
from app.infrastructure.storage import get_storage
from app.modules.analytics.api import router as analytics_router
from app.modules.auth.api import router as auth_router
from app.modules.notifications import handlers as notification_handlers
from app.modules.notifications.api import router as notifications_router
from app.modules.projects.api import router as projects_router
from app.modules.tasks.api import router as tasks_router
from app.modules.tasks.comments_api import router as comments_router
from app.modules.tasks.files_api import router as files_router
from app.modules.users.api import router as users_router
from app.shared.events import EventBus

logger = logging.getLogger("app")


def _run_alembic_upgrade() -> None:
    """Run ``alembic upgrade head`` (invoked in a worker thread — Alembic's
    async env.py calls asyncio.run, which requires no loop in this thread)."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    setup_logging(settings)
    ratelimit.configure(settings)

    if settings.run_migrations_on_startup:
        logger.info("Running database migrations")
        try:
            await anyio.to_thread.run_sync(_run_alembic_upgrade)
        except BaseException as e:
            logger.error("Database migration failed: %s", e, exc_info=True)
            raise

    engine, sessionmaker = build_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.storage = get_storage(settings)
    app.state.cache = get_cache(settings)
    app.state.queue = get_queue(settings)

    event_bus = EventBus()
    notification_handlers.register(event_bus)
    app.state.event_bus = event_bus

    logger.info(
        "%s started (env=%s, storage=%s, cache=%s, queue=%s)",
        settings.app_name,
        settings.environment.value,
        settings.storage_backend,
        settings.cache_backend,
        settings.queue_backend,
    )
    yield

    await app.state.cache.close()
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.limiter = ratelimit.limiter

    register_exception_handlers(app)

    # Starlette wraps middleware LIFO: CORS is added last so it is outermost
    # and applies its headers to error responses from inner layers too.
    app.add_middleware(SecureHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=(
            r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if settings.cors_allow_local_dev else None
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Process-Time"],
    )

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.api_v1_prefix}/docs")

    app.include_router(health_router)
    for router in (
        auth_router,
        users_router,
        projects_router,
        tasks_router,
        comments_router,
        files_router,
        notifications_router,
        analytics_router,
    ):
        app.include_router(router, prefix=settings.api_v1_prefix)

    instrument(app)  # no-op unless prometheus tooling is installed
    return app


app = create_app()
