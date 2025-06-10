import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services import comment_service
from app.models.comment import CommentCreateRequest
from app.models.user import User
from app.models.video import Video, VideoStatusEnum


@pytest.fixture
def viewer_user() -> User:
    return User(
        userid=uuid4(),
        firstname="Test",
        lastname="User",
        email="test@example.com",
        roles=["viewer"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


@pytest.fixture
def sample_video(viewer_user: User) -> Video:
    return Video(
        videoid=uuid4(),
        userid=viewer_user.userid,
        added_date=datetime.now(timezone.utc),
        name="Test Video",
        location="http://example.com/video.mp4",
        location_type=0,
        title="Test Video",
    )


@pytest.mark.asyncio
async def test_add_comment_success(viewer_user: User, sample_video: Video):
    request = CommentCreateRequest(text="Nice video!")
    sample_video.status = VideoStatusEnum.READY

    with (
        patch(
            "app.services.comment_service.video_service.get_video_by_id",
            new_callable=AsyncMock,
        ) as mock_get_vid,
        patch(
            "app.services.comment_service.get_table", new_callable=AsyncMock
        ) as mock_get_table,
    ):
        mock_get_vid.return_value = sample_video
        mock_table_video = AsyncMock()
        mock_table_user = AsyncMock()
        mock_get_table.side_effect = [mock_table_video, mock_table_user]

        comment = await comment_service.add_comment_to_video(
            video_id=sample_video.videoid,
            request=request,
            current_user=viewer_user,
        )

        assert mock_table_video.insert_one.call_count == 1
        assert mock_table_user.insert_one.call_count == 1
        assert comment.comment == request.text
        assert comment.videoid == sample_video.videoid
        assert comment.userid == viewer_user.userid
        assert comment.text == request.text


@pytest.mark.asyncio
async def test_add_comment_video_not_ready(viewer_user: User, sample_video: Video):
    request = CommentCreateRequest(text="Hello")
    sample_video.status = VideoStatusEnum.PENDING

    with patch(
        "app.services.comment_service.video_service.get_video_by_id",
        new_callable=AsyncMock,
    ) as mock_get_vid:
        mock_get_vid.return_value = sample_video
        with pytest.raises(comment_service.HTTPException) as exc_info:
            await comment_service.add_comment_to_video(
                video_id=sample_video.videoid,
                request=request,
                current_user=viewer_user,
            )
        assert exc_info.value.status_code == 404


# list tests


@pytest.mark.asyncio
async def test_list_comments_for_video():
    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = []
    mock_db.find.return_value = mock_cursor
    mock_db.count_documents.return_value = 0
    comments, total = await comment_service.list_comments_for_video(
        video_id=uuid4(), page=1, page_size=10, db_table=mock_db
    )
    assert comments == [] and total == 0


@pytest.mark.asyncio
async def test_list_comments_by_user():
    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = []
    mock_db.find.return_value = mock_cursor
    mock_db.count_documents.return_value = 0
    comments, total = await comment_service.list_comments_by_user(
        user_id=uuid4(), page=1, page_size=10, db_table=mock_db
    )
    assert comments == [] and total == 0


@pytest.mark.asyncio
async def test_get_comment_by_id_found():
    comment_id = uuid4()
    video_id = uuid4()
    sample_doc = {
        "commentid": comment_id,
        "videoid": video_id,
        "userid": uuid4(),
        "comment": "sample",
        "text": "sample",
    }

    mock_db = AsyncMock()
    mock_db.find_one.return_value = sample_doc

    comment = await comment_service.get_comment_by_id(
        comment_id=comment_id, video_id=video_id, db_table=mock_db
    )

    mock_db.find_one.assert_called_once_with(
        filter={"videoid": video_id, "commentid": comment_id}
    )
    assert comment is not None and comment.commentid == comment_id


@pytest.mark.asyncio
async def test_get_comment_by_id_not_found():
    comment_id = uuid4()
    video_id = uuid4()
    mock_db = AsyncMock()
    mock_db.find_one.return_value = None

    comment = await comment_service.get_comment_by_id(
        comment_id=comment_id, video_id=video_id, db_table=mock_db
    )

    mock_db.find_one.assert_called_once_with(
        filter={"videoid": video_id, "commentid": comment_id}
    )
    assert comment is None
