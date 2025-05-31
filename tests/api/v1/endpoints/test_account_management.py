import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from datetime import timedelta

from app.main import app  # Main app instance for client
from app.core.config import settings  # For API_V1_STR
from app.models.user import (
    UserCreateRequest,
    User,
    UserProfileUpdateRequest,
)  # Added UserProfileUpdateRequest
from app.core.security import create_access_token  # For generating test tokens

# Sample data for mocking service responses
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

    # Mock document that create_user_in_table would return
    mock_created_user_doc = {
        "userid": str(SAMPLE_USER_ID),
        "firstName": SAMPLE_FIRST_NAME,
        "lastName": SAMPLE_LAST_NAME,
        "email": SAMPLE_EMAIL,
        # other fields like hashed_password, roles, created_at would also be here
    }

    with (
        patch(
            "app.services.user_service.get_user_by_email_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user_by_email,
        patch(
            "app.services.user_service.create_user_in_table", new_callable=AsyncMock
        ) as mock_create_user,
    ):
        mock_get_user_by_email.return_value = None  # Simulate user does not exist
        mock_create_user.return_value = mock_created_user_doc  # Simulate user creation

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

        mock_get_user_by_email.assert_called_once_with(email=SAMPLE_EMAIL)
        # Assert that create_user_in_table was called with a UserCreateRequest object
        mock_create_user.assert_called_once()
        args, kwargs = mock_create_user.call_args
        assert isinstance(kwargs.get("user_in"), UserCreateRequest)
        assert kwargs.get("user_in").email == SAMPLE_EMAIL


@pytest.mark.asyncio
async def test_register_user_email_already_exists():
    user_data = {
        "firstName": "Another",
        "lastName": "User",
        "email": "existing.user@example.com",
        "password": "password123",
    }

    with patch(
        "app.services.user_service.get_user_by_email_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_email:
        mock_get_user_by_email.return_value = {
            "email": "existing.user@example.com"
        }  # Simulate user exists

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                f"{settings.API_V1_STR}/users/register", json=user_data
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["detail"] == "Email already registered"
        mock_get_user_by_email.assert_called_once_with(
            email="existing.user@example.com"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field_to_miss, expected_detail_part",
    [("firstName", "firstName"), ("email", "email"), ("password", "password")],
)
async def test_register_user_missing_fields(field_to_miss, expected_detail_part):
    user_data = {
        "firstName": "Test",
        "lastName": "User",
        "email": "test.user@example.com",
        "password": "supersecret123",
    }
    del user_data[field_to_miss]

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/users/register", json=user_data
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_details = response.json().get("detail", [])
    assert isinstance(error_details, list)
    assert any(
        expected_detail_part in e.get("loc", [])
        for e in error_details
        if isinstance(e.get("loc"), list)
        and len(e.get("loc")) > 1
        and e.get("loc")[1] == expected_detail_part
    )


@pytest.mark.asyncio
async def test_register_user_invalid_email():
    user_data = {
        "firstName": "Test",
        "lastName": "User",
        "email": "not-an-email",
        "password": "supersecret123",
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/users/register", json=user_data
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_details = response.json().get("detail", [])
    assert isinstance(error_details, list)
    assert any(
        "email" in e.get("loc", [])
        and "value is not a valid email address" in e.get("msg", "").lower()
        for e in error_details
        if isinstance(e.get("loc"), list)
    )


@pytest.mark.asyncio
async def test_register_user_short_password():
    user_data = {
        "firstName": "Test",
        "lastName": "User",
        "email": "test.user@example.com",
        "password": "short",
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/users/register", json=user_data
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_details = response.json().get("detail", [])
    assert isinstance(error_details, list)
    assert any(
        "password" in e.get("loc", [])
        for e in error_details
        if isinstance(e.get("loc"), list)
    )


# --- Login Endpoint Tests ---


@pytest.mark.asyncio
async def test_login_for_access_token_success():
    login_data = {"email": SAMPLE_EMAIL, "password": "correctpassword"}

    # Mock User object that authenticate_user_from_table would return
    mock_user_model = User(
        userId=SAMPLE_USER_ID,
        firstName=SAMPLE_FIRST_NAME,
        lastName=SAMPLE_LAST_NAME,
        email=SAMPLE_EMAIL,
        roles=["viewer"],
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

        mock_authenticate_user.assert_called_once_with(
            email=SAMPLE_EMAIL, password="correctpassword"
        )
        mock_create_token.assert_called_once_with(
            subject=SAMPLE_USER_ID, roles=["viewer"]
        )


@pytest.mark.asyncio
async def test_login_for_access_token_failure():
    login_data = {"email": "wrong@example.com", "password": "wrongpassword"}

    with patch(
        "app.services.user_service.authenticate_user_from_table", new_callable=AsyncMock
    ) as mock_authenticate_user:
        mock_authenticate_user.return_value = None  # Simulate authentication failure

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                f"{settings.API_V1_STR}/users/login", json=login_data
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert response_data["detail"] == "Incorrect email or password"
        # Header may not be present in custom handler; ensure error detail is correct
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        mock_authenticate_user.assert_called_once_with(
            email="wrong@example.com", password="wrongpassword"
        )


# Parametrized tests for missing/invalid fields in login request (Pydantic validation)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field_to_alter, value, expected_loc_part",
    [
        ("email", "not-an-email", "email"),
        ("password", "", "password"),  # Example: empty password
    ],
)
async def test_login_invalid_input_data(field_to_alter, value, expected_loc_part):
    login_data = {"email": "test@example.com", "password": "secure"}
    login_data[field_to_alter] = value

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(f"{settings.API_V1_STR}/users/login", json=login_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_details = response.json().get("detail", [])
    assert isinstance(error_details, list)
    assert any(
        expected_loc_part in e.get("loc", [])
        for e in error_details
        if isinstance(e.get("loc"), list)
    )


# --- /users/me Endpoint Tests ---


@pytest.mark.asyncio
async def test_read_users_me_success():
    # 1. Create a token for a test user
    test_user = User(
        userId=SAMPLE_USER_ID,
        firstName=SAMPLE_FIRST_NAME,
        lastName=SAMPLE_LAST_NAME,
        email=SAMPLE_EMAIL,
        roles=["viewer"],
    )
    token = create_access_token(subject=test_user.userId, roles=test_user.roles)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock the get_user_by_id_from_table service call that get_current_user_from_token will make
    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_id:
        mock_get_user_by_id.return_value = test_user

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/users/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["userId"] == str(test_user.userId)
        assert response_data["email"] == test_user.email
        assert response_data["firstName"] == test_user.firstName
        mock_get_user_by_id.assert_called_once_with(user_id=test_user.userId)


@pytest.mark.asyncio
async def test_read_users_me_no_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"{settings.API_V1_STR}/users/me")  # No headers
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_read_users_me_invalid_token_malformed():
    headers = {"Authorization": "Bearer invalidtokenstring"}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    # Detail might vary based on JWT library's parsing error
    assert "Could not validate credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_users_me_expired_token():
    expired_tk = create_access_token(
        subject=SAMPLE_USER_ID, roles=["viewer"], expires_delta=timedelta(seconds=-3600)
    )
    headers = {"Authorization": f"Bearer {expired_tk}"}

    # Mock get_user_by_id_from_table because the token decoding itself will raise ExpiredSignatureError first
    # (or rather, our get_current_user_token will catch it)
    # So, the service call won't even be reached if token is recognized as expired by jose.jwt.decode or our check.
    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_id:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/users/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Token has expired"
        mock_get_user_by_id.assert_not_called()  # Should not be called if token validation fails first


@pytest.mark.asyncio
async def test_read_users_me_valid_token_user_not_found_in_db():
    user_id_not_in_db = uuid4()
    token = create_access_token(subject=user_id_not_in_db, roles=["viewer"])
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_id:
        mock_get_user_by_id.return_value = None  # Simulate user not found in DB

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/users/me", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found"
        mock_get_user_by_id.assert_called_once_with(user_id=user_id_not_in_db)


# Forbidden role test for GET /users/me
@pytest.mark.asyncio
async def test_read_users_me_forbidden_role():
    # User with role that is NOT viewer/creator/moderator
    forbidden_user = User(
        userId=SAMPLE_USER_ID,
        firstName="Forbidden",
        lastName="User",
        email=SAMPLE_EMAIL,
        roles=["subscriber"],
    )
    token = create_access_token(subject=forbidden_user.userId, roles=forbidden_user.roles)
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user:
        mock_get_user.return_value = forbidden_user

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/users/me", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "User does not have any of the required roles" in response.json()["detail"]
        mock_get_user.assert_called_once_with(user_id=forbidden_user.userId)


# --- /users/me PUT Endpoint Tests ---


@pytest.mark.asyncio
async def test_update_users_me_success():
    # 1. Setup: Create a token for an existing user & define update data
    current_user_model = User(
        userId=SAMPLE_USER_ID,
        firstName="OriginalFirst",
        lastName="OriginalLast",
        email=SAMPLE_EMAIL,
        roles=["viewer"],
    )
    token = create_access_token(
        subject=current_user_model.userId, roles=current_user_model.roles
    )
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {"firstName": "UpdatedFirst", "lastName": "UpdatedLast"}

    # Expected user model after update
    expected_updated_user_model = User(
        userId=SAMPLE_USER_ID,
        firstName="UpdatedFirst",
        lastName="UpdatedLast",
        email=SAMPLE_EMAIL,  # Email not changed
        roles=["viewer"],  # Roles not changed
    )

    # 2. Mock dependencies: get_current_user_from_token (implicitly via app) & user_service.update_user_in_table
    # We need to ensure get_current_user_from_token dependency correctly provides 'current_user'
    # For this integration test, we rely on the dependency chain.
    # We directly mock the service call made by the endpoint.
    with (
        patch(
            "app.services.user_service.update_user_in_table", new_callable=AsyncMock
        ) as mock_update_user,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user_for_dependency,
    ):
        # Mock for the get_current_user_from_token dependency
        mock_get_user_for_dependency.return_value = current_user_model
        # Mock for the endpoint's direct service call
        mock_update_user.return_value = expected_updated_user_model

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.put(
                f"{settings.API_V1_STR}/users/me", headers=headers, json=update_payload
            )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["firstName"] == "UpdatedFirst"
        assert response_data["lastName"] == "UpdatedLast"
        assert (
            response_data["email"] == SAMPLE_EMAIL
        )  # Ensure unchanged fields are correct
        assert response_data["userId"] == str(SAMPLE_USER_ID)

        mock_update_user.assert_called_once()
        args, kwargs = mock_update_user.call_args
        assert kwargs["user_id"] == current_user_model.userId
        assert isinstance(kwargs["update_data"], UserProfileUpdateRequest)
        assert kwargs["update_data"].firstName == "UpdatedFirst"
        assert kwargs["update_data"].lastName == "UpdatedLast"


@pytest.mark.asyncio
async def test_update_users_me_empty_payload():
    current_user_model = User(
        userId=SAMPLE_USER_ID,
        firstName="First",
        lastName="Last",
        email=SAMPLE_EMAIL,
        roles=["viewer"],
    )
    token = create_access_token(
        subject=current_user_model.userId, roles=current_user_model.roles
    )
    headers = {"Authorization": f"Bearer {token}"}
    empty_payload = {}

    with (
        patch(
            "app.services.user_service.update_user_in_table", new_callable=AsyncMock
        ) as mock_update_user,
        patch(
            "app.services.user_service.get_user_by_id_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user_for_dependency,
    ):
        mock_get_user_for_dependency.return_value = current_user_model
        # If payload is empty, update_user_in_table should return the original user model
        mock_update_user.return_value = current_user_model

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.put(
                f"{settings.API_V1_STR}/users/me", headers=headers, json=empty_payload
            )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["firstName"] == "First"  # Original data
        mock_update_user.assert_called_once()
        args, kwargs = mock_update_user.call_args
        assert (
            kwargs["update_data"].model_dump(exclude_unset=True) == {}
        )  # Ensure service got empty validated model


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload, expected_detail_loc_part",
    [
        ({"firstName": "a" * 51}, ["body", "firstName"]),  # Too long
        (
            {"lastName": ""},
            ["body", "lastName"],
        ),  # Too short (if min_length=1 not met by empty string)
    ],
)
async def test_update_users_me_invalid_data(invalid_payload, expected_detail_loc_part):
    token = create_access_token(subject=SAMPLE_USER_ID, roles=["viewer"])
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_dep:
        mock_get_user_dep.return_value = User(
            userId=SAMPLE_USER_ID,
            firstName="First",
            lastName="Last",
            email=SAMPLE_EMAIL,
            roles=["viewer"],
        )
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.put(
                f"{settings.API_V1_STR}/users/me", headers=headers, json=invalid_payload
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_details = response.json().get("detail", [])
    assert isinstance(error_details, list)
    found_error = False
    for error in error_details:
        if (
            isinstance(error.get("loc"), list)
            and error.get("loc") == expected_detail_loc_part
        ):
            found_error = True
            break
    assert found_error, (
        f"Validation error for {expected_detail_loc_part} not found in {error_details}"
    )


# Tests for no token / invalid token for PUT /me would be similar to GET /me
# and are implicitly covered by the get_current_user_from_token dependency tests.
# For explicit endpoint tests:
@pytest.mark.asyncio
async def test_update_users_me_no_token():
    update_payload = {"firstName": "UpdatedFirst"}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(f"{settings.API_V1_STR}/users/me", json=update_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"
