from __future__ import annotations

import pytest

from app.services import video_service


@pytest.mark.asyncio
async def test_semantic_search_correct_sort(monkeypatch):
    # Patch list_videos_with_query to avoid hitting real DB and capture args
    captured = {}

    async def _fake_list(
        query_filter, page, page_size, sort_options, db_table=None, **kwargs
    ):  # noqa: D401
        captured["sort"] = sort_options
        return [], 0

    monkeypatch.setattr(video_service, "list_videos_with_query", _fake_list)

    await video_service.search_videos_by_semantic("cats talking", page=1, page_size=10)

    assert captured["sort"] == {"$vectorize": "cats talking"}


@pytest.mark.asyncio
async def test_semantic_search_token_limit(monkeypatch):
    # Build query with 513 tokens
    query = " ".join("tok" for _ in range(513))

    with pytest.raises(video_service.HTTPException) as exc:
        await video_service.search_videos_by_semantic(query, page=1, page_size=5)

    assert exc.value.status_code == 400
    assert "512-token" in exc.value.detail
