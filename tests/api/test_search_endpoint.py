from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import config
from app.services import video_service

client = TestClient(app)


@pytest.mark.asyncio
async def test_search_semantic_enabled(monkeypatch):
    # Enable flag
    original = getattr(config.settings, "VECTOR_SEARCH_ENABLED", None)
    object.__setattr__(config.settings, "VECTOR_SEARCH_ENABLED", True)

    # Mock semantic helper
    called = {}

    async def _semantic(query, page, page_size):  # noqa: D401
        called["query"] = query
        return [], 0

    monkeypatch.setattr(video_service, "search_videos_by_semantic", _semantic)

    resp = client.get(
        "/api/v1/search/videos", params={"query": "cats", "mode": "semantic"}
    )
    assert resp.status_code == 200
    assert called["query"] == "cats"

    # restore flag
    if original is not None:
        object.__setattr__(config.settings, "VECTOR_SEARCH_ENABLED", original)
    else:
        config.settings.__dict__.pop("VECTOR_SEARCH_ENABLED", None)


@pytest.mark.asyncio
async def test_search_keyword_fallback(monkeypatch):
    # Disable flag
    original = getattr(config.settings, "VECTOR_SEARCH_ENABLED", None)
    object.__setattr__(config.settings, "VECTOR_SEARCH_ENABLED", False)

    async def _keyword(query, page, page_size):  # noqa: D401
        return [{"videoid": "vid1"}], 1

    monkeypatch.setattr(video_service, "search_videos_by_keyword", _keyword)

    resp = client.get(
        "/api/v1/search/videos", params={"query": "dogs", "mode": "semantic"}
    )
    assert resp.status_code == 200
    # Ensure response json contains data list with one item
    assert resp.json()["pagination"]["totalItems"] == 1

    if original is not None:
        object.__setattr__(config.settings, "VECTOR_SEARCH_ENABLED", original)
    else:
        config.settings.__dict__.pop("VECTOR_SEARCH_ENABLED", None)


@pytest.mark.asyncio
async def test_search_semantic_token_limit(monkeypatch):
    original = getattr(config.settings, "VECTOR_SEARCH_ENABLED", None)
    object.__setattr__(config.settings, "VECTOR_SEARCH_ENABLED", True)

    long_query = " ".join("tok" for _ in range(513))
    resp = client.get(
        "/api/v1/search/videos", params={"query": long_query, "mode": "semantic"}
    )
    assert resp.status_code == 400

    if original is not None:
        object.__setattr__(config.settings, "VECTOR_SEARCH_ENABLED", original)
    else:
        config.settings.__dict__.pop("VECTOR_SEARCH_ENABLED", None)
