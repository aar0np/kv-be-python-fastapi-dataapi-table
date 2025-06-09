import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services import rating_service
from app.models.rating import RatingCreateOrUpdateRequest
from app.models.user import User
from app.models.video import Video, VideoStatusEnum


@pytest.fixture
def viewer_user() -> User:
    return User(
        userid=uuid4(),
        firstname="Viewer",
        lastname="Test",
        email="viewer@example.com",
        roles=["viewer"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


@pytest.mark.asyncio
async def test_rate_video_new(viewer_user: User):
    video_id = uuid4()
    req = RatingCreateOrUpdateRequest(rating=4)

    ready_video = Video(
        videoid=video_id,
        userid=uuid4(),
        added_date=datetime.now(timezone.utc),
        name="Title",
        location="http://a.b/c.mp4",
        location_type=0,
        status=VideoStatusEnum.READY,
        title="Title",
    )

    with (
        patch(
            "app.services.rating_service.video_service.get_video_by_id",
            new_callable=AsyncMock,
        ) as mock_get_vid,
        patch(
            "app.services.rating_service.get_table", new_callable=AsyncMock
        ) as mock_get_table,
    ):
        mock_get_vid.return_value = ready_video
        ratings_tbl = AsyncMock()
        videos_tbl = AsyncMock()
        mock_get_table.side_effect = [ratings_tbl, videos_tbl]

        ratings_tbl.find_one.return_value = None
        ratings_tbl.insert_one.return_value = {}
        ratings_tbl.find = MagicMock(return_value=[])
        ratings_tbl.count_documents.return_value = 0

        result = await rating_service.rate_video(
            video_id, req, viewer_user, db_table=ratings_tbl
        )
        assert result.rating == 4
        ratings_tbl.insert_one.assert_called_once()


# ---------------------------------------------------------------------------
# Existing rating update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_video_update(viewer_user: User):
    video_id = uuid4()
    req = RatingCreateOrUpdateRequest(rating=5)

    ready_video = Video(
        videoid=video_id,
        userid=uuid4(),
        added_date=datetime.now(timezone.utc),
        name="Title",
        location="http://a.b/c.mp4",
        location_type=0,
        status=VideoStatusEnum.READY,
        title="Title",
    )

    existing_doc = {
        "videoid": str(video_id),
        "userid": str(viewer_user.userid),
        "rating": 3,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    with (
        patch(
            "app.services.rating_service.video_service.get_video_by_id",
            new_callable=AsyncMock,
        ) as mock_get_vid,
        patch(
            "app.services.rating_service.get_table", new_callable=AsyncMock
        ) as mock_get_table,
        patch(
            "app.services.rating_service._update_video_aggregate_rating",
            new_callable=AsyncMock,
        ) as mock_update_agg,
    ):
        mock_get_vid.return_value = ready_video
        ratings_tbl = AsyncMock()
        videos_tbl = AsyncMock()
        mock_get_table.side_effect = [ratings_tbl, videos_tbl]

        ratings_tbl.find_one.return_value = existing_doc
        ratings_tbl.update_one.return_value = {}

        result = await rating_service.rate_video(
            video_id, req, viewer_user, db_table=ratings_tbl
        )

        ratings_tbl.update_one.assert_called_once()
        assert result.rating == req.rating
        mock_update_agg.assert_awaited_once()


# ---------------------------------------------------------------------------
# Summary fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_video_ratings_summary_with_user(viewer_user: User):
    video_id = uuid4()

    video_obj = Video(
        videoid=video_id,
        userid=uuid4(),
        added_date=datetime.now(timezone.utc),
        name="Title",
        location="http://a.b/c.mp4",
        location_type=0,
        status=VideoStatusEnum.READY,
        title="Title",
        averageRating=4.5,
        totalRatingsCount=2,
    )

    with (
        patch(
            "app.services.rating_service.video_service.get_video_by_id",
            new_callable=AsyncMock,
        ) as mock_get_vid,
        patch(
            "app.services.rating_service.get_table", new_callable=AsyncMock
        ) as mock_get_table,
    ):
        mock_get_vid.return_value = video_obj
        ratings_tbl = AsyncMock()
        mock_get_table.return_value = ratings_tbl
        ratings_tbl.find_one.return_value = {"rating": 5}

        summary = await rating_service.get_video_ratings_summary(
            video_id, current_user_id=viewer_user.userid, ratings_db_table=ratings_tbl
        )

        assert summary.averageRating == 4.5
        assert summary.totalRatingsCount == 2
        assert summary.currentUserRating == 5
