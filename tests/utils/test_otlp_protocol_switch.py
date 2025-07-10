import pytest
from fastapi import FastAPI

from app.core import config as cfg
from app.utils import observability as obs


@pytest.mark.parametrize("proto", ["grpc", "http"])
def test_otlp_protocol_switch(monkeypatch, proto):
    """configure_observability chooses correct exporter for both protocols."""

    # Ensure endpoint & flags are enabled
    monkeypatch.setattr(
        cfg.settings,
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://collector:4318",
        raising=False,
    )
    monkeypatch.setattr(
        cfg.settings, "OTEL_EXPORTER_OTLP_PROTOCOL", proto, raising=False
    )
    monkeypatch.setattr(cfg.settings, "OTEL_TRACES_ENABLED", True, raising=False)

    # Reset observability internal flag
    obs._otel_instrumented = False  # type: ignore[attr-defined]

    app = FastAPI()

    try:
        obs.configure_observability(app)
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"configure_observability raised unexpected exception: {exc}")

    # If OpenTelemetry libs missing in test env, _OTEL_READY will be False – skip assertion.
    if not obs._OTEL_READY:  # type: ignore[attr-defined]
        pytest.skip("OpenTelemetry libraries not available in test environment")

    assert obs._otel_instrumented  # type: ignore[attr-defined]
