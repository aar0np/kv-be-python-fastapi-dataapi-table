import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings
from app.models.recommendation import RecommendationItem


@pytest.mark.asyncio
async def test_get_related_videos_endpoint():
    video_id = uuid4()

    dummy_items = [
        RecommendationItem(
            videoId=uuid4(), title="Video 1", thumbnailUrl=None, score=0.9
        ),
        RecommendationItem(
            videoId=uuid4(), title="Video 2", thumbnailUrl=None, score=0.8
        ),
    ]

    with patch(
        "app.api.v1.endpoints.video_catalog.recommendation_service.get_related_videos",
        new_callable=AsyncMock,
    ) as mock_service:
        mock_service.return_value = dummy_items

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(
                f"{settings.API_V1_STR}/videos/id/{video_id}/related?limit=2"
            )

        assert response.status_code == status.HTTP_200_OK
        # FastAPI JSON serialises UUIDs as strings, so normalise our expected payload.
        expected = [
            dict(item.model_dump(), videoId=str(item.videoId)) for item in dummy_items
        ]
        assert response.json() == expected

        mock_service.assert_awaited_once_with(video_id=video_id, limit=2)
