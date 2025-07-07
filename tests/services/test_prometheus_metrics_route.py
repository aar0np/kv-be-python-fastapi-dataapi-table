from importlib import reload
from types import ModuleType

import pytest
from fastapi import FastAPI
from app.utils.observability import Instrumentator  # type: ignore

# List of (module path, attribute name) tuples for each micro-service FastAPI app
SERVICE_MODULES = [
    ("app.main_user", "service_app"),
    ("app.main_comment", "service_app"),
    ("app.main_video", "service_app"),
    ("app.main_reco", "service_app"),
    ("app.main_search", "service_app"),
    ("app.main_moderation", "service_app"),
]


@pytest.mark.parametrize("module_path, attr", SERVICE_MODULES)
def test_metrics_route_present_once(module_path: str, attr: str):
    """Ensure each micro-service exposes exactly one /metrics endpoint."""

    # Reload observability module so that its module-level flags are reset for each service
    reload(__import__("app.utils.observability", fromlist=["*"]))

    mod: ModuleType = __import__(module_path, fromlist=[attr])
    app: FastAPI = getattr(mod, attr)

    if Instrumentator is None:  # pragma: no cover
        pytest.skip(
            "prometheus_fastapi_instrumentator not installed; skipping metrics route test"
        )

    metrics_routes = [r for r in app.routes if getattr(r, "path", None) == "/metrics"]

    assert (
        len(metrics_routes) == 1
    ), f"Expected exactly one /metrics route in {module_path}, found {len(metrics_routes)}"

    # ------------------------------------------------------------------
    # Ensure custom histograms are registered and exposed even before any
    # requests have been observed.  We hit the endpoint and look for the
    # HELP/TYPE metadata lines which are always present.
    # ------------------------------------------------------------------

    from starlette.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text

    expected_metric_names = [
        "astra_db_query_duration_seconds",
        "youtube_fetch_duration_seconds",
        "vector_search_duration_seconds",
        "recommendation_generation_duration_seconds",
    ]

    for m in expected_metric_names:
        assert (
            f"# TYPE {m} histogram" in body or f"{m}_bucket" in body
        ), f"Custom metric {m} not found in /metrics output for {module_path}"
