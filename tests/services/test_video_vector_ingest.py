import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services import video_service
from app.models.video import VideoSubmitRequest
from app.models.user import User


@pytest.fixture
def test_user() -> User:  # Re-declare small fixture to avoid import chain
    return User(
        userid=uuid4(),
        firstname="Unit",
        lastname="Tester",
        email="u@example.com",
        roles=["creator"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


@pytest.mark.asyncio
async def test_submit_new_video_embeds_string(monkeypatch, test_user):
    """`content_features` must be a *string* destined for $vectorize, not a list."""

    mock_table = AsyncMock()
    # Simulate successful insert
    mock_table.insert_one.return_value = {}

    monkeypatch.setattr(video_service, "get_table", AsyncMock(return_value=mock_table))

    req = VideoSubmitRequest(youtubeUrl="https://youtu.be/abcdefghijk")

    await video_service.submit_new_video(request=req, current_user=test_user)

    # Validate inserted document
    args, kwargs = mock_table.insert_one.call_args
    doc = kwargs["document"]

    assert "content_features" in doc
    assert isinstance(doc["content_features"], str)
    # Basic sanity – should include YouTube title placeholder (Untitled) or resolved name token
    assert len(doc["content_features"]) > 0
