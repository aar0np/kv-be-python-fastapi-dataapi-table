import pytest

from app.external_services.youtube_mock import MockYouTubeService


@pytest.mark.asyncio
async def test_get_video_details_known_good():
    svc = MockYouTubeService()
    details = await svc.get_video_details("known_good_id")

    assert details is not None
    assert details["title"] == "Epic Mock Video Title"
    assert details["description"].startswith("This is a fantastic video")


@pytest.mark.asyncio
async def test_get_video_details_known_bad():
    svc = MockYouTubeService()
    details = await svc.get_video_details("known_bad_id")

    assert details is None


@pytest.mark.asyncio
async def test_get_video_details_other_id():
    svc = MockYouTubeService()
    random_id = "abcdefghijk"
    details = await svc.get_video_details(random_id)

    assert details is not None
    assert details["title"].startswith("Generic Video")
