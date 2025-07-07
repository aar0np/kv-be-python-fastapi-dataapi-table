"""Runtime patching helpers to instrument AstraDBCollection methods.

Call `instrument_astra_collection()` early during application startup (done in
`app.utils.observability`) and every `insert_one` / `update_one` will be
surrounded by an OpenTelemetry span and Prometheus histogram sample.  This
provides visibility into **all** Data-API mutations without having to wrap
each individual call site.
"""
from __future__ import annotations

import time
from typing import Any, Awaitable

from opentelemetry import trace

from app.metrics import ASTRA_DB_QUERY_DURATION_SECONDS

_tracer = trace.get_tracer(__name__)


async def _observe(op: str, coro: Awaitable[Any]):  # noqa: D401
    """Await *coro* while recording span + histogram for DB *op*."""

    start = time.perf_counter()
    with _tracer.start_as_current_span(f"astra.{op}") as span:
        try:
            result = await coro
            return result
        finally:
            duration = time.perf_counter() - start
            ASTRA_DB_QUERY_DURATION_SECONDS.labels(operation=op).observe(duration)
            span.set_attribute("duration_ms", int(duration * 1000))


def instrument_astra_collection() -> None:  # noqa: D401
    """Monkey-patch AstraDBCollection once per process."""

    try:
        from app.db.astra_client import AstraDBCollection  # type: ignore
    except Exception:
        return  # Library not available in unit-test mode

    if getattr(AstraDBCollection, "_kv_instrumented", False):
        return  # Already patched

    # ---------------------------- insert_one ----------------------------
    if hasattr(AstraDBCollection, "insert_one"):
        _orig_insert = AstraDBCollection.insert_one

        async def _insert_wrap(self, *args, **kwargs):  # type: ignore
            return await _observe("insert", _orig_insert(self, *args, **kwargs))

        AstraDBCollection.insert_one = _insert_wrap  # type: ignore[attr-defined]

    # ---------------------------- update_one ----------------------------
    if hasattr(AstraDBCollection, "update_one"):
        _orig_update = AstraDBCollection.update_one

        async def _update_wrap(self, *args, **kwargs):  # type: ignore
            return await _observe("update", _orig_update(self, *args, **kwargs))

        AstraDBCollection.update_one = _update_wrap  # type: ignore[attr-defined]

    # Mark as patched
    AstraDBCollection._kv_instrumented = True  # type: ignore[attr-defined] 