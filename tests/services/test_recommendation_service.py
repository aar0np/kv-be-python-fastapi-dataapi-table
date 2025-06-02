import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services.recommendation_service import get_related_videos
from app.models.video import Video, VideoStatusEnum, VideoSummary, VideoID
from app.models.recommendation import RecommendationItem


@pytest.fixture
def sample_video_id() -> VideoID:
    return uuid4()


@pytest.fixture
def sample_video(sample_video_id):
    return Video(
        videoId=sample_video_id,
        userId=uuid4(),
        youtubeVideoId="abcdefghijk",
        submittedAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=VideoStatusEnum.READY,
        title="Sample Video",
        description=None,
        tags=[],
        thumbnailUrl=None,
        viewCount=0,
        averageRating=None,
    )


@pytest.mark.asyncio
async def test_get_related_videos_returns_expected_items(sample_video):
    # Prepare mock latest videos list containing the source + other videos
    other_video_id_1 = uuid4()
    other_video_id_2 = uuid4()

    summaries = [
        VideoSummary(
            videoId=sample_video.videoId,
            title="Source Video",
            thumbnailUrl=None,
            userId=sample_video.userId,
            submittedAt=sample_video.submittedAt,
            viewCount=0,
            averageRating=None,
        ),
        VideoSummary(
            videoId=other_video_id_1,
            title="Other 1",
            thumbnailUrl=None,
            userId=uuid4(),
            submittedAt=datetime.now(timezone.utc),
            viewCount=0,
            averageRating=None,
        ),
        VideoSummary(
            videoId=other_video_id_2,
            title="Other 2",
            thumbnailUrl=None,
            userId=uuid4(),
            submittedAt=datetime.now(timezone.utc),
            viewCount=0,
            averageRating=None,
        ),
    ]

    with (
        patch("app.services.recommendation_service.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get_video,
        patch("app.services.recommendation_service.video_service.list_latest_videos", new_callable=AsyncMock) as mock_list_latest,
    ):
        mock_get_video.return_value = sample_video
        mock_list_latest.return_value = (summaries, len(summaries))

        items = await get_related_videos(video_id=sample_video.videoId, limit=2)

        # Should exclude source video and respect limit
        assert len(items) == 2
        assert all(isinstance(i, RecommendationItem) for i in items)
        returned_ids = {i.videoId for i in items}
        assert sample_video.videoId not in returned_ids


@pytest.mark.asyncio
async def test_get_related_videos_source_not_found(sample_video_id):
    with patch("app.services.recommendation_service.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get_video:
        mock_get_video.return_value = None

        items = await get_related_videos(video_id=sample_video_id, limit=5)
        assert items == [] 