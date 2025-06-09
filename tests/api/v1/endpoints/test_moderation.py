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
)


@pytest.fixture
def moderator_user() -> User:
    return User(
        userid=uuid4(),
        firstname="Mod",
        lastname="Erator",
        email="mod@example.com",
        roles=["moderator"],
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


@pytest.fixture
def moderator_token(moderator_user: User) -> str:
    return create_access_token(
        subject=moderator_user.userid, roles=[moderator_user.account_status]
    )


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
        patch(
            "app.api.v1.endpoints.moderation.flag_service.list_flags",
            new_callable=AsyncMock,
        ) as mock_list,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_list.return_value = ([sample_flag], 1)
        mock_get_user.return_value = moderator_user

        headers = {"Authorization": f"Bearer {moderator_token}"}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/moderation/flags?page=1&pageSize=10",
                headers=headers,
            )

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
        patch(
            "app.api.v1.endpoints.moderation.flag_service.get_flag_by_id",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_get.return_value = sample_flag
        mock_get_user.return_value = moderator_user

        headers = {"Authorization": f"Bearer {moderator_token}"}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/moderation/flags/{fid}", headers=headers
            )

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
        patch(
            "app.api.v1.endpoints.moderation.flag_service.get_flag_by_id",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.v1.endpoints.moderation.flag_service.action_on_flag",
            new_callable=AsyncMock,
        ) as mock_action,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_get.return_value = sample_flag
        mock_action.return_value = updated_flag
        mock_get_user.return_value = moderator_user

        headers = {"Authorization": f"Bearer {moderator_token}"}
        payload = {
            "status": FlagStatusEnum.REJECTED.value,
            "moderatorNotes": "Not valid.",
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(
                f"{settings.API_V1_STR}/moderation/flags/{fid}/action",
                json=payload,
                headers=headers,
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_moderation_endpoints_require_authentication():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get(
            f"{settings.API_V1_STR}/moderation/flags?page=1&pageSize=10"
        )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_search_users_endpoint(moderator_user: User, moderator_token: str):
    with (
        patch(
            "app.api.v1.endpoints.moderation.user_service.search_users",
            new_callable=AsyncMock,
        ) as mock_search,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_search.return_value = [moderator_user]
        mock_get_user.return_value = moderator_user
        headers = {"Authorization": f"Bearer {moderator_token}"}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.get(
                f"{settings.API_V1_STR}/moderation/users?q=mod", headers=headers
            )
        assert resp.status_code == status.HTTP_200_OK
        mock_search.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_revoke_moderator_endpoints(
    moderator_user: User, moderator_token: str
):
    target_id = uuid4()
    updated_user = moderator_user.model_copy(
        update={"userid": target_id, "roles": ["viewer", "moderator"]}
    )

    with (
        patch(
            "app.api.v1.endpoints.moderation.user_service.assign_role_to_user",
            new_callable=AsyncMock,
        ) as mock_assign,
        patch(
            "app.api.v1.endpoints.moderation.user_service.revoke_role_from_user",
            new_callable=AsyncMock,
        ) as mock_revoke,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user,
    ):
        mock_assign.return_value = updated_user
        mock_revoke.return_value = updated_user.model_copy(update={"roles": ["viewer"]})
        mock_get_user.return_value = moderator_user
        headers = {"Authorization": f"Bearer {moderator_token}"}

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp_assign = await ac.post(
                f"{settings.API_V1_STR}/moderation/users/{target_id}/assign-moderator",
                headers=headers,
            )
            resp_revoke = await ac.post(
                f"{settings.API_V1_STR}/moderation/users/{target_id}/revoke-moderator",
                headers=headers,
            )
        assert resp_assign.status_code == status.HTTP_200_OK
        assert resp_revoke.status_code == status.HTTP_200_OK
        mock_assign.assert_awaited_once()
        mock_revoke.assert_awaited_once()
