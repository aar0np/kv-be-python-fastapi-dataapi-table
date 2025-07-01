# Observability utilities – OpenTelemetry instrumentation, Prometheus metrics
# exposition and structured log shipping.
#
# This module is imported by main.py during application start-up.  All
# instrumentation is performed in a best-effort fashion: if a particular
# dependency is missing or an endpoint is unreachable we log a warning but
# allow the application to continue running.

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI

from app.core.config import settings

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prometheus – latency histogram per route via prometheus-fastapi-instrumentator
# ---------------------------------------------------------------------------

_PROMETHEUS_READY = False

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Instrumentator = None  # type: ignore
    _logger.debug("prometheus_fastapi_instrumentator not available – metrics disabled")


# ---------------------------------------------------------------------------
# OpenTelemetry – traces + optional OTLP metric export
# ---------------------------------------------------------------------------

_OTEL_READY = False
try:
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore
    from opentelemetry.instrumentation.logging import LoggingInstrumentor  # type: ignore
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    # Metrics are optional – only import if feature flag enabled
    if settings.OTEL_METRICS_ENABLED:
        from opentelemetry.sdk.metrics import MeterProvider  # type: ignore
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # type: ignore
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics.export import (
            PeriodicExportingMetricReader,
        )

    _OTEL_READY = True
except ModuleNotFoundError as exc:  # pragma: no cover
    _logger.debug("OpenTelemetry libraries missing – traces disabled (%s)", exc)


# ---------------------------------------------------------------------------
# Loki logging handler
# ---------------------------------------------------------------------------

_LOKI_READY = False
if settings.LOKI_ENABLED and settings.LOKI_ENDPOINT:
    try:
        import logging_loki  # type: ignore

        _LOKI_READY = True
    except ModuleNotFoundError:  # pragma: no cover
        _logger.warning("LOKI_ENABLED but logging_loki dependency missing; skipping Loki handler")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure_observability(app: FastAPI) -> None:  # noqa: D401
    """Initialise optional observability integrations.

    The function is safe to call multiple times – it keeps track of internal
    state to ensure instrumentation happens only once.
    """

    if not settings.OBSERVABILITY_ENABLED:
        _logger.info("Observability explicitly disabled via settings")
        return

    _setup_prometheus(app)
    _setup_opentelemetry(app)
    _setup_loki_logging()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_prometheus_instrumented = False

def _setup_prometheus(app: FastAPI) -> None:
    global _prometheus_instrumented
    if _prometheus_instrumented or Instrumentator is None:
        return

    try:
        start_time = time.perf_counter()
        Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)
        _prometheus_instrumented = True
        _logger.info("Prometheus instrumentation initialised in %.2f ms", (time.perf_counter() - start_time) * 1000)
    except Exception as exc:  # pragma: no cover
        _logger.warning("Failed to initialise Prometheus instrumentation: %s", exc)


_otel_instrumented = False

def _setup_opentelemetry(app: FastAPI) -> None:
    global _otel_instrumented
    if _otel_instrumented or not _OTEL_READY or not settings.OTEL_TRACES_ENABLED:
        return

    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        _logger.info("OTEL_TRACES_ENABLED but no OTEL_EXPORTER_OTLP_ENDPOINT set – skipping")
        return

    try:
        start = time.perf_counter()

        resource_attrs: dict[str, Any] = {
            "service.name": settings.PROJECT_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
        resource = Resource.create(resource_attrs)

        sampler = TraceIdRatioBased(settings.OTEL_TRACES_SAMPLER_RATIO)
        provider = TracerProvider(resource=resource, sampler=sampler)
        trace.set_tracer_provider(provider)

        span_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        span_processor = BatchSpanProcessor(span_exporter)
        provider.add_span_processor(span_processor)

        # Instrument FastAPI request handling
        FastAPIInstrumentor().instrument_app(app, tracer_provider=provider)

        # Correlate application logs with active spans
        LoggingInstrumentor().instrument(set_logging_format=True)

        # Optional metrics export via OTLP
        if settings.OTEL_METRICS_ENABLED:
            metric_exporter = OTLPMetricExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
            reader = PeriodicExportingMetricReader(metric_exporter)
            meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            from opentelemetry import metrics  # local import to avoid missing module issue

            metrics.set_meter_provider(meter_provider)

        _otel_instrumented = True
        _logger.info("OpenTelemetry tracing initialised (%.2f ms)", (time.perf_counter() - start) * 1000)
    except Exception as exc:  # pragma: no cover
        _logger.warning("Failed to initialise OpenTelemetry tracing: %s", exc)


_loki_handler_added = False

def _setup_loki_logging() -> None:
    global _loki_handler_added
    if _loki_handler_added or not _LOKI_READY:
        return

    try:
        import logging_loki  # type: ignore

        tags = {
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
        }
        if settings.LOKI_EXTRA_LABELS:
            for pair in settings.LOKI_EXTRA_LABELS.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    tags[k.strip()] = v.strip()

        handler = logging_loki.LokiHandler(
            url=settings.LOKI_ENDPOINT,  # type: ignore[arg-type]
            tags=tags,
            version="1",
        )
        logging.getLogger().addHandler(handler)
        _loki_handler_added = True
        _logger.info("Loki logging handler attached (endpoint=%s)", settings.LOKI_ENDPOINT)
    except Exception as exc:  # pragma: no cover
        _logger.warning("Failed to attach Loki logging handler: %s", exc) 