"""Metrics / observability hooks.

The architecture is Prometheus- and OpenTelemetry-ready without hard
dependencies: when ``prometheus-fastapi-instrumentator`` (or the OTel SDK) is
installed and enabled here, instrumentation attaches in ``create_app``.
Until then this module is a documented no-op, and per-request timing is already
exposed via the ``X-Process-Time`` header and structured access logs.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger("app.metrics")


def instrument(app: FastAPI) -> None:
    """Attach metrics instrumentation when the optional tooling is available.

    To enable Prometheus metrics::

        pip install prometheus-fastapi-instrumentator

    which exposes ``/metrics`` for scraping (wire Grafana dashboards on top).
    For distributed tracing, install ``opentelemetry-instrumentation-fastapi``
    and configure an OTLP exporter — the request/correlation IDs emitted by
    RequestContextMiddleware line up with trace attributes.
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        logger.debug("Prometheus instrumentator not installed; metrics endpoint disabled")
        return
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
