import importlib
import logging
from types import ModuleType

import pytest
from fastapi import FastAPI

from app.core import config as cfg


@pytest.mark.parametrize("loki_enabled", [True, False])
def test_logging_handler_selection(tmp_path, monkeypatch, loki_enabled):
    """When Loki enabled and lib present we attach LokiHandler, else RotatingFileHandler."""

    # Temp log dir
    monkeypatch.chdir(tmp_path)

    # Patch settings at runtime
    monkeypatch.setattr(cfg.settings, "LOKI_ENABLED", loki_enabled, raising=False)
    monkeypatch.setattr(
        cfg.settings, "LOKI_ENDPOINT", "http://dummy:3100", raising=False
    )

    # Reset root handlers to avoid cross-param contamination
    logging.getLogger().handlers.clear()

    # Re-import observability to reset flags
    obs = importlib.reload(importlib.import_module("app.utils.observability"))

    # Monkeypatch logging_loki availability based on scenario
    if loki_enabled:

        class DummyLokiHandler(logging.Handler):
            def __init__(self, *args, **kwargs):  # accept arbitrary Loki kwargs
                super().__init__()

            def emit(self, record):  # noqa: D401
                # Simply drop log records in tests
                return

        dummy_module = ModuleType("logging_loki")
        dummy_module.LokiHandler = DummyLokiHandler  # type: ignore[attr-defined]
        monkeypatch.setitem(importlib.sys.modules, "logging_loki", dummy_module)
        obs._LOKI_READY = True  # type: ignore[attr-defined]
    else:
        # Ensure module import fails
        if "logging_loki" in importlib.sys.modules:
            del importlib.sys.modules["logging_loki"]
        obs._LOKI_READY = False  # type: ignore[attr-defined]

    # Run configurator
    app = FastAPI()
    obs.configure_observability(app)

    handler_types = {type(h).__name__ for h in logging.getLogger().handlers}

    if loki_enabled:
        assert "DummyLokiHandler" in handler_types
    else:
        assert "RotatingFileHandler" in handler_types
