import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings
from app.models.video import VideoSummary, TagSuggestion


@pytest.mark.asyncio
async def test_search_videos_success():
    sample_summary = VideoSummary(
        videoId=uuid4(),
        title="Test Title",
        thumbnailUrl=None,
        userId=uuid4(),
        submittedAt=datetime.now(timezone.utc),
        viewCount=0,
        averageRating=4.5,
    )

    with patch(
        "app.api.v1.endpoints.search_catalog.video_service.search_videos_by_keyword",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = ([sample_summary], 1)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/search/videos",
                params={"query": "test", "page": 1, "pageSize": 10},
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_videos_missing_query():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get(f"{settings.API_V1_STR}/search/videos")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_tag_suggestions_success():
    suggestions = [TagSuggestion(tag="python"), TagSuggestion(tag="fastapi")]
    with patch(
        "app.api.v1.endpoints.search_catalog.video_service.suggest_tags",
        new_callable=AsyncMock,
    ) as mock_suggest:
        mock_suggest.return_value = suggestions
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/search/tags/suggest",
                params={"query": "py", "limit": 5},
            )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 2
        mock_suggest.assert_awaited_once()


@pytest.mark.asyncio
async def test_tag_suggestions_missing_query():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get(f"{settings.API_V1_STR}/search/tags/suggest")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
