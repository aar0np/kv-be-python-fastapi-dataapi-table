import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.comment import Comment
from app.models.user import User
from app.models.rating import Rating, AggregateRatingResponse


@pytest.fixture
def viewer_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Viewer",
        lastName="Tester",
        email="viewer@example.com",
        roles=["viewer"],
    )


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    return create_access_token(subject=viewer_user.userId, roles=viewer_user.roles)


@pytest.mark.asyncio
async def test_post_comment_success(viewer_user: User, viewer_token: str):
    sample_comment = Comment(
        commentId=uuid4(),
        videoId=uuid4(),
        userId=viewer_user.userId,
        text="Great video!",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        sentiment="positive",
    )

    with (
        patch(
            "app.api.v1.endpoints.comments_ratings.comment_service.add_comment_to_video",
            new_callable=AsyncMock,
        ) as mock_add,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_add.return_value = sample_comment
        mock_get_user.return_value = viewer_user

        headers = {"Authorization": f"Bearer {viewer_token}"}
        payload = {"text": "Great video!"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(
                f"{settings.API_V1_STR}/videos/{sample_comment.videoId}/comments",
                json=payload,
                headers=headers,
            )

        assert resp.status_code == status.HTTP_201_CREATED
        mock_add.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_comment_no_token():
    payload = {"text": "Nice!"}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            f"{settings.API_V1_STR}/videos/{uuid4()}/comments",
            json=payload,
        )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# list comments endpoints


@pytest.mark.asyncio
async def test_list_video_comments():
    with patch(
        "app.api.v1.endpoints.comments_ratings.comment_service.list_comments_for_video",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/videos/{uuid4()}/comments?page=1&pageSize=10"
            )
        assert resp.status_code == status.HTTP_200_OK
        mock_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_user_comments():
    with patch(
        "app.api.v1.endpoints.comments_ratings.comment_service.list_comments_by_user",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/users/{uuid4()}/comments?page=1&pageSize=10"
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_list.assert_awaited_once()


# ----------------------------- Ratings POST -----------------------------


@pytest.mark.asyncio
async def test_post_rating_success(viewer_user: User, viewer_token: str):
    sample_rating = Rating(
        videoId=uuid4(),
        userId=viewer_user.userId,
        rating=4,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )

    with patch(
        "app.api.v1.endpoints.comments_ratings.rating_service.rate_video",
        new_callable=AsyncMock,
    ) as mock_rate, patch(
        "app.services.user_service.get_user_by_id_from_table",
        new_callable=AsyncMock,
    ) as mock_get_user:
        mock_rate.return_value = sample_rating
        mock_get_user.return_value = viewer_user

        headers = {"Authorization": f"Bearer {viewer_token}"}
        payload = {"rating": 4}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(
                f"{settings.API_V1_STR}/videos/{sample_rating.videoId}/ratings",
                json=payload,
                headers=headers,
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_rate.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_rating_no_token():
    payload = {"rating": 3}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            f"{settings.API_V1_STR}/videos/{uuid4()}/ratings",
            json=payload,
        )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ----------------------------- Ratings GET -----------------------------


@pytest.mark.asyncio
async def test_get_rating_summary_public():
    video_id = uuid4()
    agg = AggregateRatingResponse(
        videoId=video_id,
        averageRating=4.0,
        totalRatingsCount=3,
        currentUserRating=None,
    )

    with patch(
        "app.api.v1.endpoints.comments_ratings.rating_service.get_video_ratings_summary",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = agg

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(f"{settings.API_V1_STR}/videos/{video_id}/ratings")

        assert resp.status_code == status.HTTP_200_OK
        mock_get.assert_awaited_once() 