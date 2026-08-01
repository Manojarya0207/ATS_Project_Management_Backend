# Deployment Guide

## Environments

Behaviour is driven by `ENVIRONMENT` (see `app/core/config.py`):

| | development | testing | staging | production |
|---|---|---|---|---|
| Database | SQLite ok | in-memory SQLite | Postgres | **Postgres required** |
| Logs | console | console | JSON | JSON |
| Weak `JWT_SECRET_KEY` | allowed | allowed | allowed | **boot refused** |
| `DEBUG=true` | allowed | allowed | allowed | **boot refused** |

Production startup **fails fast** on: default/short JWT secret, SQLite URL, or
debug mode — misconfiguration is caught at deploy time, not at 3 a.m.

## Docker (recommended)

```bash
cp .env.example .env
# Set at minimum:
#   JWT_SECRET_KEY=$(openssl rand -hex 32)
#   POSTGRES_PASSWORD=<strong password>
docker compose up -d --build
```

- The image is multi-stage (builder venv → slim runtime), runs as a non-root
  `app` user, and has a `/health` HEALTHCHECK.
- Migrations run automatically at startup (`RUN_MIGRATIONS_ON_STARTUP=true`).
  For multi-replica deployments, set it to `false` and run migrations as a
  release step instead: `alembic upgrade head`.
- Seed the first admin: `docker compose exec api python scripts/seed_admin.py <email> <password>`.

## Kubernetes / orchestrators

- **Liveness probe**: `GET /health/live` (process up).
- **Readiness probe**: `GET /health/ready` (verifies DB connectivity; returns
  503 while dependencies are down so traffic is held).
- Run migrations as a Job/init container (`alembic upgrade head`) and set
  `RUN_MIGRATIONS_ON_STARTUP=false`.
- Horizontal scaling: the API is stateless. With more than one replica:
  - move uploads off local disk (`STORAGE_BACKEND=s3` or `r2`/`azure`),
  - use `CACHE_BACKEND=redis` (the in-memory cache is per-process),
  - keep rate limiting fair by fronting with an ingress limiter, or point
    slowapi at Redis.

## Observability

- Structured JSON logs on stdout — ship with your collector of choice
  (Loki, ELK, CloudWatch). Every line carries `request_id`/`correlation_id`.
- Pass `X-Correlation-ID` from upstream services to stitch traces together.
- Prometheus: `pip install prometheus-fastapi-instrumentator` exposes
  `/metrics` automatically (see `app/infrastructure/monitoring/metrics.py`);
  point Grafana at it.
- Per-request latency is also returned in the `X-Process-Time` header.

## Checklist before going live

- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET_KEY` = 32+ random chars (e.g. `openssl rand -hex 32`)
- [ ] `DATABASE_URL` = managed Postgres with backups
- [ ] `CORS_ORIGINS` = your real frontend origins; `CORS_ALLOW_LOCAL_DEV=false`
- [ ] `STORAGE_BACKEND` ≠ local if running more than one replica
- [ ] TLS terminated at the load balancer / ingress
- [ ] Log shipping + alerting wired
- [ ] `scripts/verify_e2e.py` passes against the deployed URL (adjust `BASE`)
