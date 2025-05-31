import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.video import Video, VideoStatusEnum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_video(owner_id):
    """Return a deterministic Video instance for mocking purposes."""

    return Video(
        videoId=uuid4(),
        userId=owner_id,
        youtubeVideoId="abcdefghijk",
        submittedAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=VideoStatusEnum.PENDING,
        title="Video Title Pending Processing",
        description=None,
        tags=[],
        thumbnailUrl=None,
        viewCount=0,
        averageRating=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def creator_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Creator",
        lastName="User",
        email="creator@example.com",
        roles=["creator"],
    )


@pytest.fixture
def creator_token(creator_user: User) -> str:
    return create_access_token(subject=creator_user.userId, roles=creator_user.roles)


@pytest.fixture
def viewer_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Viewer",
        lastName="User",
        email="viewer@example.com",
        roles=["viewer"],
    )


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    return create_access_token(subject=viewer_user.userId, roles=viewer_user.roles)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_video_success(creator_user: User, creator_token: str):
    sample_video = _make_video(owner_id=creator_user.userId)

    with (
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
        patch(
            "app.api.v1.endpoints.video_catalog.video_service.submit_new_video",
            new_callable=AsyncMock,
        ) as mock_submit_video,
        patch(
            "app.api.v1.endpoints.video_catalog.video_service.process_video_submission",
            new_callable=AsyncMock,
        ) as mock_process_video,
    ):
        mock_get_user.return_value = creator_user
        mock_submit_video.return_value = sample_video

        headers = {"Authorization": f"Bearer {creator_token}"}
        payload = {"youtubeUrl": "https://youtu.be/abcdefghijk"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"{settings.API_V1_STR}/videos", json=payload, headers=headers)

        assert response.status_code == status.HTTP_202_ACCEPTED
        resp_json = response.json()
        assert resp_json["videoId"] == str(sample_video.videoId)
        # submit_new_video should have been called with VideoSubmitRequest-like param and current_user
        mock_submit_video.assert_awaited_once()
        # Background task should have been executed once after response lifecycle
        mock_process_video.assert_awaited_once_with(
            sample_video.videoId, sample_video.youtubeVideoId
        )


@pytest.mark.asyncio
async def test_submit_video_forbidden_role(viewer_user: User, viewer_token: str):

    with patch(
        "app.services.user_service.get_user_by_id_from_table",
        new_callable=AsyncMock,
    ) as mock_get_user:
        mock_get_user.return_value = viewer_user

        headers = {"Authorization": f"Bearer {viewer_token}"}
        payload = {"youtubeUrl": "https://youtu.be/abcdefghijk"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"{settings.API_V1_STR}/videos", json=payload, headers=headers)

        # Viewer lacks creator/moderator role -> 403
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_submit_video_unauthenticated():
    payload = {"youtubeUrl": "https://youtu.be/abcdefghijk"}

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(f"{settings.API_V1_STR}/videos", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_submit_video_invalid_url(creator_user: User, creator_token: str):
    from fastapi import HTTPException

    with (
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
        patch(
            "app.api.v1.endpoints.video_catalog.video_service.submit_new_video",
            new_callable=AsyncMock,
        ) as mock_submit_video,
    ):
        mock_get_user.return_value = creator_user
        mock_submit_video.side_effect = HTTPException(status_code=400, detail="Invalid YouTube URL")

        headers = {"Authorization": f"Bearer {creator_token}"}
        payload = {"youtubeUrl": "https://example.com/notyoutube"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"{settings.API_V1_STR}/videos", json=payload, headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid YouTube URL"


# ------------------------------------------------------------
# GET /videos/{id}/status & /videos/{id}
# ------------------------------------------------------------


@pytest.fixture
def moderator_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Mod",
        lastName="User",
        email="mod@example.com",
        roles=["moderator"],
    )


@pytest.fixture
def moderator_token(moderator_user: User) -> str:
    return create_access_token(subject=moderator_user.userId, roles=moderator_user.roles)


@pytest.mark.asyncio
async def test_get_video_status_owner(creator_user: User, creator_token: str):
    video = _make_video(owner_id=creator_user.userId)

    with (
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
        patch(
            "app.api.v1.endpoints.video_catalog.video_service.get_video_by_id",
            new_callable=AsyncMock,
        ) as mock_get_video,
    ):
        mock_get_user.return_value = creator_user
        mock_get_video.return_value = video

        headers = {"Authorization": f"Bearer {creator_token}"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/videos/id/{video.videoId}/status", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == video.status


@pytest.mark.asyncio
async def test_get_video_status_forbidden(viewer_user: User, viewer_token: str):
    video = _make_video(owner_id=uuid4())

    with (
        patch("app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock) as mock_get_user,
        patch("app.api.v1.endpoints.video_catalog.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get_video,
    ):
        mock_get_user.return_value = viewer_user
        mock_get_video.return_value = video

        headers = {"Authorization": f"Bearer {viewer_token}"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/videos/id/{video.videoId}/status", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_video_details_public():
    video = _make_video(owner_id=uuid4())

    with patch(
        "app.api.v1.endpoints.video_catalog.video_service.get_video_by_id",
        new_callable=AsyncMock,
    ) as mock_get_video:
        mock_get_video.return_value = video

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/videos/id/{video.videoId}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["videoId"] == str(video.videoId)


# Latest videos endpoint


@pytest.mark.asyncio
async def test_get_latest_videos():
    with patch(
        "app.api.v1.endpoints.video_catalog.video_service.list_latest_videos",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/videos/latest?page=1&pageSize=10")

        if response.status_code != status.HTTP_200_OK:
            print('DEBUG latest resp', response.status_code, response.json())
        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_awaited_once()


# Record view endpoint


@pytest.mark.asyncio
async def test_record_view_success():
    video = _make_video(owner_id=uuid4())
    video.status = VideoStatusEnum.READY

    with (
        patch("app.api.v1.endpoints.video_catalog.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get,
        patch("app.api.v1.endpoints.video_catalog.video_service.record_video_view", new_callable=AsyncMock) as mock_record,
    ):
        mock_get.return_value = video
        mock_record.return_value = True

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"{settings.API_V1_STR}/videos/id/{video.videoId}/view")

        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_record_view_not_ready():
    video = _make_video(owner_id=uuid4())  # status PENDING

    with patch("app.api.v1.endpoints.video_catalog.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = video

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(f"{settings.API_V1_STR}/videos/id/{video.videoId}/view")

        assert response.status_code == status.HTTP_404_NOT_FOUND 