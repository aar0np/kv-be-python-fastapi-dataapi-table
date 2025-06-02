import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.services import flag_service
from app.models.flag import ContentTypeEnum, FlagCreateRequest, FlagReasonCodeEnum, FlagStatusEnum, Flag
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


# --- Additional tests for list/get/action ---

@pytest.mark.asyncio
async def test_list_flags_with_status_filter():
    sample_flag_doc = {
        "flagId": str(uuid4()),
        "userId": str(uuid4()),
        "contentType": ContentTypeEnum.VIDEO.value,
        "contentId": str(uuid4()),
        "reasonCode": FlagReasonCodeEnum.SPAM.value,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "status": FlagStatusEnum.OPEN.value,
    }

    mock_db = AsyncMock()
    mock_db.find = MagicMock(return_value=[sample_flag_doc])
    mock_db.count_documents.return_value = 1

    flags, total = await flag_service.list_flags(
        page=1, page_size=10, status_filter=FlagStatusEnum.OPEN, db_table=mock_db
    )

    mock_db.find.assert_called_once()
    assert total == 1 and len(flags) == 1 and flags[0].flagId == UUID(sample_flag_doc["flagId"])


@pytest.mark.asyncio
async def test_get_flag_by_id_found():
    fid = uuid4()
    doc = {
        "flagId": str(fid),
        "userId": str(uuid4()),
        "contentType": ContentTypeEnum.VIDEO.value,
        "contentId": str(uuid4()),
        "reasonCode": FlagReasonCodeEnum.SPAM.value,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "status": FlagStatusEnum.OPEN.value,
    }

    mock_db = AsyncMock()
    mock_db.find_one.return_value = doc

    flag = await flag_service.get_flag_by_id(flag_id=fid, db_table=mock_db)

    mock_db.find_one.assert_called_once_with(filter={"flagId": str(fid)})
    assert flag is not None and flag.flagId == fid


@pytest.mark.asyncio
async def test_action_on_flag_updates_status():
    fid = uuid4()
    now = datetime.now(timezone.utc)
    initial_flag = Flag(
        flagId=fid,
        userId=uuid4(),
        contentType=ContentTypeEnum.VIDEO,
        contentId=uuid4(),
        reasonCode=FlagReasonCodeEnum.SPAM,
        createdAt=now,
        updatedAt=now,
    )

    moderator_user = User(
        userId=uuid4(),
        firstName="Mod",
        lastName="Erator",
        email="mod@example.com",
        roles=["moderator"],
    )

    mock_db = AsyncMock()
    mock_db.update_one.return_value = MagicMock()

    updated_flag = await flag_service.action_on_flag(
        flag_to_action=initial_flag,
        new_status=FlagStatusEnum.APPROVED,
        moderator_notes="Looks bad",
        moderator=moderator_user,
        db_table=mock_db,
    )

    mock_db.update_one.assert_called_once()
    assert updated_flag.status == FlagStatusEnum.APPROVED
    assert updated_flag.moderatorId == moderator_user.userId 