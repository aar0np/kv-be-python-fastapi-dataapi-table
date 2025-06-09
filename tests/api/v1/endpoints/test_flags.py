import pytest
from uuid import uuid4
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from fastapi import status

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.flag import Flag, FlagReasonCodeEnum, ContentTypeEnum, FlagStatusEnum
from app.models.user import User


@pytest.fixture
def viewer_user() -> User:
    return User(
        userid=uuid4(),
        firstname="View",
        lastname="Er",
        email="view@example.com",
        roles=["viewer"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    return create_access_token(
        subject=viewer_user.userid, roles=[viewer_user.account_status]
    )


@pytest.mark.asyncio
async def test_post_flag_success(viewer_user: User, viewer_token: str):
    sample_flag = Flag(
        flagId=uuid4(),
        userId=viewer_user.userid,
        contentType=ContentTypeEnum.VIDEO,
        contentId=uuid4(),
        reasonCode=FlagReasonCodeEnum.SPAM,
        reasonText="spam",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=FlagStatusEnum.OPEN,
    )

    with (
        patch(
            "app.api.v1.endpoints.flags.flag_service.create_flag",
            new_callable=AsyncMock,
        ) as mock_create,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_create.return_value = sample_flag
        mock_get_user.return_value = viewer_user

        headers = {"Authorization": f"Bearer {viewer_token}"}
        payload = {
            "contentType": ContentTypeEnum.VIDEO.value,
            "contentId": str(sample_flag.contentId),
            "reasonCode": FlagReasonCodeEnum.SPAM.value,
            "reasonText": "spam",
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(
                f"{settings.API_V1_STR}/flags", json=payload, headers=headers
            )

        assert resp.status_code == status.HTTP_201_CREATED
        mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_flag_no_token():
    payload = {
        "contentType": ContentTypeEnum.VIDEO.value,
        "contentId": str(uuid4()),
        "reasonCode": FlagReasonCodeEnum.SPAM.value,
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(f"{settings.API_V1_STR}/flags", json=payload)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
