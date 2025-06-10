import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services import video_service
from app.models.video import (
    VideoSubmitRequest,
    VideoStatusEnum,
    Video,
    VideoUpdateRequest,
)
from app.models.user import User


# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------


@pytest.fixture
def test_user() -> User:
    """Return a minimal User object with a *creator* role for tests."""
    return User(
        userid=uuid4(),
        firstname="Unit",
        lastname="Tester",
        email="unittest@example.com",
        roles=["creator"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


# ------------------------------------------------------------
# extract_youtube_video_id
# ------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://youtu.be/abcdefghijk", "abcdefghijk"),
        ("http://youtu.be/abcdefghijk", "abcdefghijk"),
        ("https://www.youtube.com/watch?v=abcdefghijk", "abcdefghijk"),
        ("https://youtube.com/watch?v=abcdefghijk", "abcdefghijk"),
        ("https://www.youtube.com/embed/abcdefghijk", "abcdefghijk"),
        ("https://www.youtube.com/v/abcdefghijk", "abcdefghijk"),
        ("https://www.youtube.com/shorts/abcdefghijk", "abcdefghijk"),
    ],
)
def test_extract_youtube_video_id_valid(url: str, expected: str):
    assert video_service.extract_youtube_video_id(url) == expected


def test_extract_youtube_video_id_invalid():
    assert (
        video_service.extract_youtube_video_id("https://example.com/notyoutube") is None
    )


# ------------------------------------------------------------
# submit_new_video
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_new_video_success(test_user: User):
    request = VideoSubmitRequest(youtubeUrl="https://youtu.be/abcdefghijk")

    # Prepare mocks
    mock_db_table = AsyncMock()
    mock_db_table.insert_one.return_value = MagicMock(inserted_id="someid")

    # Patch uuid4 to deterministic value for assertion
    deterministic_video_id = uuid4()
    with patch("app.services.video_service.uuid4", return_value=deterministic_video_id):
        new_video = await video_service.submit_new_video(
            request=request, current_user=test_user, db_table=mock_db_table
        )

    # Assertions on DB insert
    mock_db_table.insert_one.assert_called_once()
    args, kwargs = mock_db_table.insert_one.call_args
    inserted_doc = kwargs.get("document")
    assert inserted_doc is not None
    assert inserted_doc["videoid"] == deterministic_video_id
    assert inserted_doc["userid"] == test_user.userid
    assert inserted_doc["youtubeVideoId"] == "abcdefghijk"
    assert inserted_doc["status"] == video_service.VideoStatusEnum.PENDING

    # Assertions on returned model
    assert isinstance(new_video, Video)
    assert new_video.videoid == deterministic_video_id
    assert new_video.userid == test_user.userid
    assert new_video.youtubeVideoId == "abcdefghijk"
    assert new_video.status == VideoStatusEnum.PENDING


@pytest.mark.asyncio
async def test_submit_new_video_invalid_url(test_user: User):
    request = VideoSubmitRequest(youtubeUrl="https://example.com/notyoutube")
    mock_db_table = AsyncMock()

    with pytest.raises(video_service.HTTPException) as exc_info:
        await video_service.submit_new_video(
            request=request, current_user=test_user, db_table=mock_db_table
        )

    assert exc_info.value.status_code == 400
    mock_db_table.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_submit_new_video_uses_get_table_when_none(test_user: User):
    request = VideoSubmitRequest(youtubeUrl="https://youtu.be/abcdefghijk")

    with patch(
        "app.services.video_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        mock_actual_table = AsyncMock()
        mock_actual_table.insert_one.return_value = MagicMock(inserted_id="someid")
        mock_get_table.return_value = mock_actual_table

        await video_service.submit_new_video(request=request, current_user=test_user)

        mock_get_table.assert_called_once_with(video_service.VIDEOS_TABLE_NAME)
        mock_actual_table.insert_one.assert_called_once()


# ------------------------------------------------------------
# get_video_by_id
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_video_by_id_found(test_user: User):
    target_video = _build_video()

    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = target_video.model_dump(by_alias=False)

    result = await video_service.get_video_by_id(
        video_id=target_video.videoid, db_table=mock_db_table
    )

    mock_db_table.find_one.assert_called_once_with(
        filter={"videoid": target_video.videoid}
    )
    assert result == target_video


@pytest.mark.asyncio
async def test_get_video_by_id_not_found():
    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = None

    result = await video_service.get_video_by_id(
        video_id=uuid4(), db_table=mock_db_table
    )
    assert result is None


# helper function for building video inside tests


def _build_video():
    return Video(
        videoid=uuid4(),
        userid=uuid4(),
        added_date=datetime.now(timezone.utc),
        name="Title",
        location="http://example.com/video.mp4",
        location_type=0,
    )


# ------------------------------------------------------------
# update_video_details
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_video_details_success():
    original_video = _build_video()
    update_req = VideoUpdateRequest(name="New Title", description="New desc")

    mock_db_table = AsyncMock()
    mock_db_table.update_one.return_value = AsyncMock()
    # Mock the re-fetch call
    updated_doc = original_video.model_dump(by_alias=False)
    updated_doc.update(update_req.model_dump(by_alias=False, exclude_unset=True))
    mock_db_table.find_one.return_value = updated_doc

    result = await video_service.update_video_details(
        video_to_update=original_video,
        update_request=update_req,
        db_table=mock_db_table,
    )

    mock_db_table.update_one.assert_called_once()
    assert result.name == "New Title"
    assert result.description == "New desc"


@pytest.mark.asyncio
async def test_update_video_details_no_changes():
    original_video = _build_video()
    update_req = VideoUpdateRequest()

    mock_db_table = AsyncMock()

    result = await video_service.update_video_details(
        video_to_update=original_video,
        update_request=update_req,
        db_table=mock_db_table,
    )

    mock_db_table.update_one.assert_not_called()
    assert result == original_video


# ------------------------------------------------------------
# record_video_view
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_video_view_success():
    vid = uuid4()

    # Mock the playback stats table passed explicitly
    mock_stats_table = AsyncMock()
    mock_stats_table.update_one.return_value = AsyncMock()

    # Mock the activity table returned via get_table
    mock_activity_table = AsyncMock()

    with patch(
        "app.services.video_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        # First call inside record_video_view is for VIDEO_PLAYBACK_STATS_TABLE_NAME
        # but we already pass mock_stats_table, so get_table will be used only once
        mock_get_table.return_value = mock_activity_table

        await video_service.record_video_view(vid, mock_stats_table)

        # Validate stats table increment
        mock_stats_table.update_one.assert_called_once_with(
            filter={"videoid": vid}, update={"$inc": {"views": 1}}, upsert=True
        )

        # Validate activity table log
        mock_activity_table.insert_one.assert_called_once()


# ------------------------------------------------------------
# list_latest_videos (delegate to generic) – just verify query call
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_latest_videos():
    mock_db = AsyncMock()
    mock_db.find.return_value = []
    mock_db.count_documents.return_value = 0

    with patch(
        "app.services.video_service.list_videos_with_query",
        new_callable=AsyncMock,
    ) as mock_list_with_query:
        mock_list_with_query.return_value = ([], 0)

        summaries, total = await video_service.list_latest_videos(1, 10, mock_db)

        mock_list_with_query.assert_called_once_with(
            {},
            1,
            10,
            db_table=mock_db,
            source_table_name=video_service.LATEST_VIDEOS_TABLE_NAME,
        )
        assert summaries == []
        assert total == 0


# ------------------------------------------------------------
# search_videos_by_keyword
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_videos_by_keyword():
    mock_db = AsyncMock()
    mock_db.find.return_value = []
    mock_db.count_documents.return_value = 0

    with patch(
        "app.services.video_service.list_videos_with_query",
        new_callable=AsyncMock,
    ) as mock_list_with_query:
        mock_list_with_query.return_value = ([], 0)

        summaries, total = await video_service.search_videos_by_keyword(
            query="test", page=1, page_size=10, db_table=mock_db
        )

        mock_list_with_query.assert_called_once()
        assert summaries == []
        assert total == 0


# ------------------------------------------------------------
# suggest_tags
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_tags_matching():
    # Simulate three docs with tags
    docs = [
        {"tags": ["python", "fastapi"]},
        {"tags": ["backend", "python"]},
        {"tags": ["video", "catalog"]},
    ]

    mock_db = AsyncMock()
    mock_db.find.return_value = docs

    suggestions = await video_service.suggest_tags("py", limit=5, db_table=mock_db)
    assert any(s.tag == "python" for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_tags_no_match():
    mock_db = AsyncMock()
    mock_db.find.return_value = []

    suggestions = await video_service.suggest_tags("nomatch", limit=5, db_table=mock_db)
    assert suggestions == []


# ------------------------------------------------------------
# process_video_submission
# ------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.video_service.MockYouTubeService")
@patch("app.services.video_service.get_table")
@patch("app.services.video_service.asyncio.sleep", new_callable=AsyncMock)
async def test_process_video_submission_success(
    mock_sleep, mock_get_table, mock_mock_yt
):  # noqa: D401,E501
    """Verify happy path where YouTube details are found and status transitions
    PENDING -> PROCESSING -> READY.
    """

    # Arrange mocks
    mock_instance = mock_mock_yt.return_value
    mock_instance.get_video_details = AsyncMock(
        return_value={
            "title": "Unit Test Title",
            "description": "Unit Test Desc",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "tags": ["test"],
        }
    )

    db_mock = AsyncMock()
    mock_get_table.return_value = db_mock

    vid = uuid4()

    # Act
    await video_service.process_video_submission(vid, "known_good_id")

    # Assert
    # Expect two calls to update_one: first PROCESSING, then READY
    assert db_mock.update_one.call_count == 2

    first_call_kwargs = db_mock.update_one.call_args_list[0].kwargs
    assert (
        first_call_kwargs["update"]["$set"]["status"]
        == video_service.VideoStatusEnum.PROCESSING.value
    )
    assert first_call_kwargs["update"]["$set"]["name"] == "Unit Test Title"

    second_call_kwargs = db_mock.update_one.call_args_list[1].kwargs
    assert (
        second_call_kwargs["update"]["$set"]["status"]
        == video_service.VideoStatusEnum.READY.value
    )


@pytest.mark.asyncio
@patch("app.services.video_service.MockYouTubeService")
@patch("app.services.video_service.get_table")
@patch("app.services.video_service.asyncio.sleep", new_callable=AsyncMock)
async def test_process_video_submission_failure(
    mock_sleep, mock_get_table, mock_mock_yt
):  # noqa: D401,E501
    """Verify path where YouTube details *aren't* found leading to ERROR status."""

    mock_instance = mock_mock_yt.return_value
    mock_instance.get_video_details = AsyncMock(return_value=None)

    db_mock = AsyncMock()
    mock_get_table.return_value = db_mock

    vid = uuid4()

    await video_service.process_video_submission(vid, "known_bad_id")

    # Only one DB update expected when details not found (ERROR status)
    db_mock.update_one.assert_called_once()
    call_kwargs = db_mock.update_one.call_args.kwargs
    assert (
        call_kwargs["update"]["$set"]["status"]
        == video_service.VideoStatusEnum.ERROR.value
    )


# ------------------------------------------------------------
# list_trending_videos
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_trending_videos_counts_and_order():
    """Verify that trending aggregation counts views and orders by desc."""

    # Prepare mock activity documents for 2 video IDs
    vid1, vid2 = str(uuid4()), str(uuid4())

    # Suppose vid1 has 3 views, vid2 has 1 view in window
    activity_docs_day = [
        {"videoid": vid1},
        {"videoid": vid2},
        {"videoid": vid1},
        {"videoid": vid1},
    ]

    mock_activity_table = MagicMock()
    mock_activity_table.find.return_value = activity_docs_day

    # Metadata for videos
    video_meta_docs = [
        {
            "videoid": vid1,
            "name": "Video 1",
            "preview_image_location": "https://example.com/1.jpg",
            "userid": str(uuid4()),
            "added_date": datetime.now(timezone.utc),
        },
        {
            "videoid": vid2,
            "name": "Video 2",
            "preview_image_location": "https://example.com/2.jpg",
            "userid": str(uuid4()),
            "added_date": datetime.now(timezone.utc),
        },
    ]

    mock_videos_table = MagicMock()
    mock_videos_table.find.return_value = video_meta_docs

    trending = await video_service.list_trending_videos(
        interval_days=1,
        limit=10,
        activity_table=mock_activity_table,
        videos_table=mock_videos_table,
    )

    # Expect 2 items, vid1 first due to higher view count
    assert len(trending) == 2
    assert str(trending[0].videoid) == vid1
    assert trending[0].viewCount == 3
    assert str(trending[1].videoid) == vid2
    assert trending[1].viewCount == 1
