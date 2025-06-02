import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services import flag_service
from app.models.flag import ContentTypeEnum, FlagCreateRequest, FlagReasonCodeEnum, FlagStatusEnum
from app.models.user import User
from app.models.video import Video, VideoStatusEnum


@pytest.fixture
def viewer_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Flag",
        lastName="Tester",
        email="flag@example.com",
        roles=["viewer"],
    )


@pytest.mark.asyncio
async def test_create_flag_video_success(viewer_user: User):
    video_id = uuid4()

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

    flag_request = FlagCreateRequest(
        contentType=ContentTypeEnum.VIDEO,
        contentId=video_id,
        reasonCode=FlagReasonCodeEnum.SPAM,
        reasonText="spam",
    )

    with (
        patch("app.services.flag_service.video_service.get_video_by_id", new_callable=AsyncMock) as mock_get_video,
        patch("app.services.flag_service.comment_service.get_comment_by_id", new_callable=AsyncMock) as mock_get_comment,
        patch("app.services.flag_service.get_table", new_callable=AsyncMock) as mock_get_table,
    ):
        mock_get_video.return_value = ready_video
        mock_get_comment.return_value = None
        mock_db_table = AsyncMock()
        mock_get_table.return_value = mock_db_table
        mock_db_table.insert_one.return_value = MagicMock()

        new_flag = await flag_service.create_flag(
            request=flag_request, current_user=viewer_user, db_table=mock_db_table
        )

        assert new_flag.contentId == video_id
        assert new_flag.status == FlagStatusEnum.OPEN
        mock_db_table.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_create_flag_content_not_found(viewer_user: User):
    comment_id = uuid4()

    flag_request = FlagCreateRequest(
        contentType=ContentTypeEnum.COMMENT,
        contentId=comment_id,
        reasonCode=FlagReasonCodeEnum.SPAM,
    )

    with (
        patch("app.services.flag_service.comment_service.get_comment_by_id", new_callable=AsyncMock) as mock_get_comment,
        patch("app.services.flag_service.get_table", new_callable=AsyncMock) as mock_get_table,
    ):
        mock_get_comment.return_value = None  # comment not found
        mock_get_table.return_value = AsyncMock()

        with pytest.raises(flag_service.HTTPException) as exc_info:
            await flag_service.create_flag(request=flag_request, current_user=viewer_user)

        assert exc_info.value.status_code == 404 