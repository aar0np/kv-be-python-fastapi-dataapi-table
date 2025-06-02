import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.recommendation import EmbeddingIngestResponse
from app.models.user import User


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


@pytest.mark.asyncio
async def test_ingest_embedding_success(creator_user: User, creator_token: str):
    video_id = uuid4()

    with patch(
        "app.api.v1.endpoints.reco_internal.recommendation_service.ingest_video_embedding",
        new_callable=AsyncMock,
    ) as mock_service, patch(
        "app.services.user_service.get_user_by_id_from_table",
        new_callable=AsyncMock,
    ) as mock_get_user:
        mock_service.return_value = EmbeddingIngestResponse(
            videoId=video_id,
            status="received_stub",
            message="ok",
        )
        mock_get_user.return_value = creator_user

        headers = {"Authorization": f"Bearer {creator_token}"}
        payload = {"videoId": str(video_id), "vector": [0.1, 0.2, 0.3]}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(f"{settings.API_V1_STR}/reco/ingest", json=payload, headers=headers)

        assert resp.status_code == status.HTTP_202_ACCEPTED
        mock_service.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_embedding_video_not_found(creator_user: User, creator_token: str):
    video_id = uuid4()

    with patch(
        "app.api.v1.endpoints.reco_internal.recommendation_service.ingest_video_embedding",
        new_callable=AsyncMock,
    ) as mock_service, patch(
        "app.services.user_service.get_user_by_id_from_table",
        new_callable=AsyncMock,
    ) as mock_get_user:
        mock_service.return_value = EmbeddingIngestResponse(
            videoId=video_id,
            status="error",
            message="Video not found.",
        )
        mock_get_user.return_value = creator_user

        headers = {"Authorization": f"Bearer {creator_token}"}
        payload = {"videoId": str(video_id), "vector": [0.1]}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(f"{settings.API_V1_STR}/reco/ingest", json=payload, headers=headers)

        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_ingest_embedding_requires_creator(viewer_user: User, viewer_token: str):
    video_id = uuid4()

    with patch(
        "app.services.user_service.get_user_by_id_from_table",
        new_callable=AsyncMock,
    ) as mock_get_user:
        mock_get_user.return_value = viewer_user

        headers = {"Authorization": f"Bearer {viewer_token}"}
        payload = {"videoId": str(video_id), "vector": [0.1]}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(f"{settings.API_V1_STR}/reco/ingest", json=payload, headers=headers)

        assert resp.status_code == status.HTTP_403_FORBIDDEN 