# syntax=docker/dockerfile:1

# --- Builder stage: install dependencies into an isolated virtualenv ---------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
# Install runtime dependencies only (project itself copied in the final stage)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip uninstall -y ats-project-management-backend

# --- Runtime stage: slim image, non-root user, healthcheck -------------------
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app app

WORKDIR /code

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini pyproject.toml ./
COPY --chown=app:app scripts ./scripts

RUN mkdir -p /code/uploads && chown app:app /code/uploads

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Migrations run in the application lifespan (RUN_MIGRATIONS_ON_STARTUP=true).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
