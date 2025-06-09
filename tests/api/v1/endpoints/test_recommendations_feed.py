import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.video import VideoSummary


@pytest.fixture
def viewer_user() -> User:
    return User(
        userid=uuid4(),
        firstname="Viewer",
        lastname="User",
        email="viewer@example.com",
        roles=["viewer"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    return create_access_token(
        subject=viewer_user.userid, roles=[viewer_user.account_status]
    )


@pytest.mark.asyncio
async def test_foryou_endpoint_success(viewer_user: User, viewer_token: str):
    sample_summary = VideoSummary(
        videoid=uuid4(),
        name="Video",
        preview_image_location=None,
        userid=uuid4(),
        added_date=datetime.now(timezone.utc),
        title="Video",
    )

    with (
        patch(
            "app.api.v1.endpoints.recommendations_feed.recommendation_service.get_personalized_for_you_videos",
            new_callable=AsyncMock,
        ) as mock_service,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_service.return_value = ([sample_summary], 1)
        mock_get_user.return_value = viewer_user

        headers = {"Authorization": f"Bearer {viewer_token}"}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/recommendations/foryou?page=1&pageSize=10",
                headers=headers,
            )

        if resp.status_code != status.HTTP_200_OK:
            print("DEBUG response", resp.status_code, resp.json())
        assert resp.status_code == status.HTTP_200_OK
        mock_service.assert_awaited_once()
        json_body = resp.json()
        assert json_body["pagination"]["totalItems"] == 1
        assert json_body["data"][0]["title"] == "Video"


@pytest.mark.asyncio
async def test_foryou_endpoint_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get(
            f"{settings.API_V1_STR}/recommendations/foryou?page=1&pageSize=10"
        )

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
