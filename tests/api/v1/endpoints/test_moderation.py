import pytest
from uuid import uuid4
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from fastapi import status

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.flag import (
    Flag,
    ContentTypeEnum,
    FlagReasonCodeEnum,
    FlagStatusEnum,
    FlagUpdateRequest,
)


@pytest.fixture
def moderator_user() -> User:
    return User(
        userId=uuid4(),
        firstName="Mod",
        lastName="Erator",
        email="mod@example.com",
        roles=["moderator"],
    )


@pytest.fixture
def moderator_token(moderator_user: User) -> str:
    return create_access_token(subject=moderator_user.userId, roles=moderator_user.roles)


@pytest.mark.asyncio
async def test_list_flags_endpoint(moderator_user: User, moderator_token: str):
    sample_flag = Flag(
        flagId=uuid4(),
        userId=uuid4(),
        contentType=ContentTypeEnum.VIDEO,
        contentId=uuid4(),
        reasonCode=FlagReasonCodeEnum.SPAM,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=FlagStatusEnum.OPEN,
    )

    with (
        patch("app.api.v1.endpoints.moderation.flag_service.list_flags", new_callable=AsyncMock) as mock_list,
        patch("app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_list.return_value = ([sample_flag], 1)
        mock_get_user.return_value = moderator_user

        headers = {"Authorization": f"Bearer {moderator_token}"}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(f"{settings.API_V1_STR}/moderation/flags?page=1&pageSize=10", headers=headers)

        assert resp.status_code == status.HTTP_200_OK
        mock_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_flag_details_endpoint(moderator_user: User, moderator_token: str):
    fid = uuid4()
    sample_flag = Flag(
        flagId=fid,
        userId=uuid4(),
        contentType=ContentTypeEnum.VIDEO,
        contentId=uuid4(),
        reasonCode=FlagReasonCodeEnum.SPAM,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=FlagStatusEnum.OPEN,
    )

    with (
        patch("app.api.v1.endpoints.moderation.flag_service.get_flag_by_id", new_callable=AsyncMock) as mock_get,
        patch("app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_get.return_value = sample_flag
        mock_get_user.return_value = moderator_user

        headers = {"Authorization": f"Bearer {moderator_token}"}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(f"{settings.API_V1_STR}/moderation/flags/{fid}", headers=headers)

        assert resp.status_code == status.HTTP_200_OK
        mock_get.assert_awaited_once_with(flag_id=fid)


@pytest.mark.asyncio
async def test_action_on_flag_endpoint(moderator_user: User, moderator_token: str):
    fid = uuid4()
    sample_flag = Flag(
        flagId=fid,
        userId=uuid4(),
        contentType=ContentTypeEnum.VIDEO,
        contentId=uuid4(),
        reasonCode=FlagReasonCodeEnum.SPAM,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status=FlagStatusEnum.OPEN,
    )
    updated_flag = sample_flag.model_copy(update={"status": FlagStatusEnum.REJECTED})

    with (
        patch("app.api.v1.endpoints.moderation.flag_service.get_flag_by_id", new_callable=AsyncMock) as mock_get,
        patch("app.api.v1.endpoints.moderation.flag_service.action_on_flag", new_callable=AsyncMock) as mock_action,
        patch("app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_get.return_value = sample_flag
        mock_action.return_value = updated_flag
        mock_get_user.return_value = moderator_user

        headers = {"Authorization": f"Bearer {moderator_token}"}
        payload = {"status": FlagStatusEnum.REJECTED.value, "moderatorNotes": "Not valid."}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(f"{settings.API_V1_STR}/moderation/flags/{fid}/action", json=payload, headers=headers)

        assert resp.status_code == status.HTTP_200_OK
        mock_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_moderation_endpoints_require_authentication():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get(f"{settings.API_V1_STR}/moderation/flags?page=1&pageSize=10")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED 