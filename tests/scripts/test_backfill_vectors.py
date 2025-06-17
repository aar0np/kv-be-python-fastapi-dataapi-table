from __future__ import annotations

from typing import List, Dict, Any

import pytest
from unittest.mock import AsyncMock
import types
import httpx

from scripts import backfill_vectors as bf

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubVideosTable:  # noqa: D401 – minimal async behaviour
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs_first = docs
        self._calls = 0

    def find(self, **kwargs):  # noqa: D401
        self._calls += 1
        if self._calls == 1:
            return self._docs_first
        return []  # Second call → stop loop


@pytest.mark.asyncio
async def test_backfill_vectors_dry_run(monkeypatch):
    """Verify that no Data API request is sent when --dry-run is used."""

    sample_docs = [
        {
            "videoid": "vid1",
            "name": "Title 1",
            "description": "Desc 1",
            "tags": ["cat", "talk"],
        }
    ]

    stub_table = _StubVideosTable(sample_docs)
    monkeypatch.setattr(bf, "get_table", AsyncMock(return_value=stub_table))

    called = False

    def _no_call(_):  # noqa: D401
        nonlocal called
        called = True

    monkeypatch.setattr(bf, "_execute_update_many", _no_call)

    await bf.backfill_vectors(dry_run=True, page_size=10)

    assert not called  # Should not call execute_update in dry-run mode


@pytest.mark.asyncio
async def test_backfill_vectors_update_many(monkeypatch):
    """Ensure updateMany POST is sent with correct payload."""

    sample_docs = [
        {
            "videoid": "vid2",
            "name": "Title 2",
            "description": "Desc 2",
            "tags": ["foo", "bar"],
        }
    ]

    stub_table = _StubVideosTable(sample_docs)
    monkeypatch.setattr(bf, "get_table", AsyncMock(return_value=stub_table))

    # Fake settings
    monkeypatch.setattr(bf.settings, "ASTRA_DB_API_ENDPOINT", "https://api.test")
    monkeypatch.setattr(bf.settings, "ASTRA_DB_APPLICATION_TOKEN", "tok")

    captured: dict | None = None

    def _fake_post(url, headers=None, json=None, timeout=30):  # noqa: D401
        nonlocal captured
        captured = {"url": url, "headers": headers, "json": json}

        resp = types.SimpleNamespace()

        def _raise():  # noqa: D401
            return None

        resp.raise_for_status = _raise
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)

    await bf.backfill_vectors(dry_run=False, page_size=10)

    assert captured is not None
    assert captured["json"] is not None and "operations" in captured["json"]
    op = captured["json"]["operations"][0]
    assert op["filter"]["videoid"] == "vid2"
    assert "$vectorize" in op["update"]["$set"]["content_features"]
