import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from app.main import app
from app.core.config import settings
from app.models.user import User, UserCreateRequest
from app.core.security import create_access_token

SAMPLE_USER_ID = uuid4()
SAMPLE_EMAIL = "test.user@example.com"
SAMPLE_FIRST_NAME = "Test"
SAMPLE_LAST_NAME = "User"


@pytest.mark.asyncio
async def test_register_user_success():
    user_data = {
        "firstName": SAMPLE_FIRST_NAME,
        "lastName": SAMPLE_LAST_NAME,
        "email": SAMPLE_EMAIL,
        "password": "supersecret123",
    }

    mock_created_user_doc = {
        "userid": SAMPLE_USER_ID,
        "firstname": SAMPLE_FIRST_NAME,
        "lastname": SAMPLE_LAST_NAME,
        "email": SAMPLE_EMAIL,
    }

    with (
        patch(
            "app.services.user_service.get_user_by_email_from_credentials_table",
            new_callable=AsyncMock,
        ) as mock_get_user_by_email,
        patch(
            "app.services.user_service.create_user_in_table", new_callable=AsyncMock
        ) as mock_create_user,
    ):
        mock_get_user_by_email.return_value = None
        mock_create_user.return_value = mock_created_user_doc

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                f"{settings.API_V1_STR}/users/register", json=user_data
            )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["userId"] == str(SAMPLE_USER_ID)
        assert response_data["firstName"] == SAMPLE_FIRST_NAME
        assert response_data["lastName"] == SAMPLE_LAST_NAME
        assert response_data["email"] == SAMPLE_EMAIL


@pytest.mark.asyncio
async def test_login_for_access_token_success():
    login_data = {"email": SAMPLE_EMAIL, "password": "correctpassword"}

    mock_user_model = User(
        userid=SAMPLE_USER_ID,
        firstname=SAMPLE_FIRST_NAME,
        lastname=SAMPLE_LAST_NAME,
        email=SAMPLE_EMAIL,
        account_status="active",
        created_date=datetime.now(timezone.utc),
    )

    with (
        patch(
            "app.services.user_service.authenticate_user_from_table",
            new_callable=AsyncMock,
        ) as mock_authenticate_user,
        patch(
            "app.api.v1.endpoints.account_management.create_access_token"
        ) as mock_create_token,
    ):
        mock_authenticate_user.return_value = mock_user_model
        mock_create_token.return_value = "mocked_jwt_token_string"

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                f"{settings.API_V1_STR}/users/login", json=login_data
            )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["token"] == "mocked_jwt_token_string"
        assert response_data["user"]["userId"] == str(SAMPLE_USER_ID)
        assert response_data["user"]["email"] == SAMPLE_EMAIL


@pytest.mark.asyncio
async def test_read_users_me_success():
    test_user = User(
        userid=SAMPLE_USER_ID,
        firstname=SAMPLE_FIRST_NAME,
        lastname=SAMPLE_LAST_NAME,
        email=SAMPLE_EMAIL,
        account_status="active",
        created_date=datetime.now(timezone.utc),
        roles=["viewer"],
    )
    token = create_access_token(subject=test_user.userid, roles=test_user.roles)
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_id:
        mock_get_user_by_id.return_value = test_user

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/users/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["userId"] == str(test_user.userid)
        assert response_data["email"] == test_user.email
        assert response_data["firstName"] == test_user.firstname 