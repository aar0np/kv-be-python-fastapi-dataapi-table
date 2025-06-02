import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services import comment_service
from app.models.comment import CommentCreateRequest
from app.models.user import User
from app.models.video import Video, VideoStatusEnum


@pytest.mark.asyncio
async def test_determine_sentiment_returns_valid_option():
    sentiment = await comment_service._determine_sentiment("great video")
    assert sentiment in {"positive", "neutral", "negative", None}


@pytest.fixture
def viewer_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Test",
        lastName="User",
        email="test@example.com",
        roles=["viewer"],
    )


@pytest.mark.asyncio
async def test_add_comment_success(viewer_user: User):
    video_id = uuid4()
    request = CommentCreateRequest(text="Nice video!")

    # Mock video ready
    ready_video = Video(
        videoId=video_id,
        userId=uuid4(),
        youtubeVideoId="abc",
        submittedAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=VideoStatusEnum.READY,
        title="Title",
        description=None,
        tags=[],
        thumbnailUrl=None,
        viewCount=0,
        averageRating=None,
    )

    with (
        patch("app.services.comment_service.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get_vid,
        patch("app.services.comment_service.get_table", new_callable=AsyncMock) as mock_get_table,
    ):
        mock_get_vid.return_value = ready_video
        mock_table = AsyncMock()
        mock_get_table.return_value = mock_table

        comment = await comment_service.add_comment_to_video(
            video_id=video_id, request=request, current_user=viewer_user, db_table=mock_table
        )

        mock_table.insert_one.assert_called_once()
        assert comment.text == request.text
        assert comment.videoId == video_id
        assert comment.userId == viewer_user.userId


@pytest.mark.asyncio
async def test_add_comment_video_not_ready(viewer_user: User):
    video_id = uuid4()
    request = CommentCreateRequest(text="Hello")

    not_ready_video = Video(
        videoId=video_id,
        userId=uuid4(),
        youtubeVideoId="abc",
        submittedAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=VideoStatusEnum.PENDING,
        title="Title",
        description=None,
        tags=[],
        thumbnailUrl=None,
        viewCount=0,
        averageRating=None,
    )

    with patch("app.services.comment_service.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get_vid:
        mock_get_vid.return_value = not_ready_video
        with pytest.raises(comment_service.HTTPException) as exc_info:
            await comment_service.add_comment_to_video(
                video_id=video_id, request=request, current_user=viewer_user, db_table=AsyncMock()
            )
        assert exc_info.value.status_code == 404


# list tests


@pytest.mark.asyncio
async def test_list_comments_for_video():
    mock_db = AsyncMock()
    mock_db.find = MagicMock(return_value=[])
    mock_db.count_documents.return_value = 0
    comments, total = await comment_service.list_comments_for_video(
        video_id=uuid4(), page=1, page_size=10, db_table=mock_db
    )
    assert comments == [] and total == 0


@pytest.mark.asyncio
async def test_list_comments_by_user():
    mock_db = AsyncMock()
    mock_db.find = MagicMock(return_value=[])
    mock_db.count_documents.return_value = 0
    comments, total = await comment_service.list_comments_by_user(
        user_id=uuid4(), page=1, page_size=10, db_table=mock_db
    )
    assert comments == [] and total == 0 