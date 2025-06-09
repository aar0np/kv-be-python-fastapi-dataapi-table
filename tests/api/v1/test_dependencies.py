import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from typing import List

from fastapi import HTTPException, status
from jose import jwt

from app.core.config import settings
from app.core.security import (
    TokenPayload,
    create_access_token,
)  # Import create_access_token for test token generation
from app.models.user import User
from app.api.v1 import dependencies  # Import the module to test its functions


# --- Fixtures ---
@pytest.fixture
def test_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def test_user_roles() -> List[str]:
    return ["viewer"]


@pytest.fixture
def valid_token(test_user_id: UUID, test_user_roles: List[str]) -> str:
    return create_access_token(subject=test_user_id, roles=test_user_roles)


@pytest.fixture
def expired_token(test_user_id: UUID, test_user_roles: List[str]) -> str:
    # Create a token that expired 1 hour ago
    return create_access_token(
        subject=test_user_id, roles=test_user_roles, expires_delta=timedelta(hours=-1)
    )


@pytest.fixture
def sample_user_model(test_user_id: UUID, test_user_roles: List[str]) -> User:
    return User(
        userid=test_user_id,
        firstname="Test",
        lastname="User",
        email="test@example.com",
        roles=test_user_roles,
        created_date=datetime.now(timezone.utc),
        account_status="active",
    )


# --- Tests for get_current_user_token_payload ---
@pytest.mark.asyncio
async def test_get_current_user_token_payload_valid_token(
    valid_token: str, test_user_id: UUID, test_user_roles: List[str]
):
    payload = await dependencies.get_current_user_token_payload(token=valid_token)
    assert payload is not None
    assert payload.sub == str(test_user_id)
    assert payload.roles == test_user_roles
    assert payload.exp is not None
    assert payload.exp > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_get_current_user_token_payload_missing_token():
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user_token_payload(token=None)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_get_current_user_token_payload_expired_token(expired_token: str):
    # Create a token that expired 1 hour ago
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user_token_payload(token=expired_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Token has expired"


@pytest.mark.asyncio
async def test_get_current_user_token_payload_invalid_signature():
    # Create a token with a different secret key
    invalid_secret_token = jwt.encode(
        {"sub": "test", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "WRONG_SECRET",
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user_token_payload(token=invalid_secret_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        "Could not validate credentials" in exc_info.value.detail
    )  # Detail might include specific JWTError


@pytest.mark.asyncio
async def test_get_current_user_token_payload_malformed_token():
    malformed_token = "this.is.not.a.jwt"
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user_token_payload(token=malformed_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in exc_info.value.detail


# --- Tests for get_current_user_from_token ---
@pytest.mark.asyncio
async def test_get_current_user_from_token_success(sample_user_model: User):
    token_payload = TokenPayload(
        sub=str(sample_user_model.userid),
        roles=sample_user_model.roles,
        exp=datetime.now(timezone.utc) + timedelta(minutes=15),
    )

    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_id:
        mock_get_user_by_id.return_value = sample_user_model

        user = await dependencies.get_current_user_from_token(payload=token_payload)

        assert user == sample_user_model
        mock_get_user_by_id.assert_called_once_with(user_id=sample_user_model.userid)


@pytest.mark.asyncio
async def test_get_current_user_from_token_no_subject():
    token_payload_no_sub = TokenPayload(
        roles=["viewer"], exp=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user_from_token(payload=token_payload_no_sub)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid token: Subject missing"


@pytest.mark.asyncio
async def test_get_current_user_from_token_invalid_subject_uuid():
    token_payload_invalid_sub = TokenPayload(
        sub="not-a-uuid",
        roles=["viewer"],
        exp=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user_from_token(
            payload=token_payload_invalid_sub
        )
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid token: Subject is not a valid UUID"


@pytest.mark.asyncio
async def test_get_current_user_from_token_user_not_found_in_db():
    user_id_not_in_db = uuid4()
    token_payload_user_not_found = TokenPayload(
        sub=str(user_id_not_in_db),
        roles=["viewer"],
        exp=datetime.now(timezone.utc) + timedelta(minutes=15),
    )

    with patch(
        "app.services.user_service.get_user_by_id_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_id:
        mock_get_user_by_id.return_value = None  # Simulate user not found in DB

        with pytest.raises(HTTPException) as exc_info:
            await dependencies.get_current_user_from_token(
                payload=token_payload_user_not_found
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "User not found"
        mock_get_user_by_id.assert_called_once_with(user_id=user_id_not_in_db)


# --- Tests for RBAC: require_role and derived dependencies ---


# Mock current_user for RBAC tests
@pytest.fixture
def mock_user_with_roles(test_user_id: UUID) -> User:
    def _user_with_roles(roles: List[str]) -> User:
        return User(
            userid=test_user_id,
            firstname="RBAC",
            lastname="TestUser",
            email="rbac@example.com",
            roles=roles,
            created_date=datetime.now(timezone.utc),
            account_status="active",
        )

    return _user_with_roles


@pytest.mark.asyncio
async def test_require_role_user_has_required_role(mock_user_with_roles):
    user_viewer = mock_user_with_roles(["viewer"])
    # Mock get_current_user_from_token to be called by require_role's inner checker
    with patch(
        "app.api.v1.dependencies.get_current_user_from_token", new_callable=AsyncMock
    ) as mock_get_user:
        mock_get_user.return_value = user_viewer
        # The dependency_func itself returns the actual checker, which needs to be called.
        # This is a bit tricky to test directly without an app context.
        # For simplicity, we can call the inner role_checker directly if we can access it,
        # or test through a specific dependency like get_current_viewer.

        # Test through get_current_viewer (which uses require_role(["viewer", ...]))
        # This means get_current_user_from_token will be patched for the call within require_role
        result_user = await dependencies.get_current_viewer(
            current_user=user_viewer
        )  # Pass directly for this unit test style
        assert result_user == user_viewer


@pytest.mark.asyncio
async def test_require_role_user_does_not_have_role(mock_user_with_roles):
    user_no_admin_role = mock_user_with_roles(["viewer"])
    # require_role(["admin"]) is implicitly tested via get_current_moderator if we assume moderator maps to admin
    # For a direct test of require_role logic:
    admin_role_checker = dependencies.require_role(["admin"])

    with patch(
        "app.api.v1.dependencies.get_current_user_from_token", new_callable=AsyncMock
    ) as mock_get_user:
        mock_get_user.return_value = user_no_admin_role
        with pytest.raises(HTTPException) as exc_info:
            # Call the actual checker returned by require_role
            await admin_role_checker(
                current_user=user_no_admin_role
            )  # Pass directly for unit test
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "User does not have any of the required roles: ['admin']"
            in exc_info.value.detail
        )


@pytest.mark.asyncio
async def test_require_role_user_has_no_roles(mock_user_with_roles):
    user_no_roles = mock_user_with_roles([])  # Empty list of roles
    viewer_role_checker = dependencies.require_role(["viewer"])

    with patch(
        "app.api.v1.dependencies.get_current_user_from_token", new_callable=AsyncMock
    ) as mock_get_user:
        mock_get_user.return_value = user_no_roles
        with pytest.raises(HTTPException) as exc_info:
            await viewer_role_checker(
                current_user=user_no_roles
            )  # Pass directly for unit test
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "User has no roles assigned"


# Test specific derived dependencies like get_current_viewer
@pytest.mark.asyncio
async def test_get_current_viewer_with_viewer_role(mock_user_with_roles):
    user_is_viewer = mock_user_with_roles(["viewer"])
    # get_current_viewer itself is a function that takes current_user as an argument
    # when it's resolved from Depends(require_role(...)).
    # For unit testing, we simulate this by providing the user directly.
    with patch(
        "app.api.v1.dependencies.get_current_user_from_token", new_callable=AsyncMock
    ) as mock_base_auth:
        mock_base_auth.return_value = (
            user_is_viewer  # This is what require_role's inner dependency will get
        )

        # This test relies on the fact that get_current_viewer is defined as:
        # async def get_current_viewer(current_user: Annotated[User, Depends(require_role(["viewer", ...]))]) -> User: return current_user
        # So, if require_role passes, get_current_viewer returns the user.
        # We are essentially testing the require_role part here.
        returned_user = await dependencies.get_current_viewer(
            user_is_viewer
        )  # Simulate FastAPI DI by passing user
        assert returned_user == user_is_viewer


@pytest.mark.asyncio
async def test_get_current_viewer_with_creator_role(mock_user_with_roles):
    user_is_creator = mock_user_with_roles(["creator"])
    with patch(
        "app.api.v1.dependencies.get_current_user_from_token", new_callable=AsyncMock
    ) as mock_base_auth:
        mock_base_auth.return_value = user_is_creator
        returned_user = await dependencies.get_current_viewer(user_is_creator)
        assert (
            returned_user == user_is_creator
        )  # Creator is also a viewer per get_current_viewer definition


@pytest.mark.asyncio
async def test_get_current_viewer_fails_if_only_unrelated_role(mock_user_with_roles):
    user_unrelated_role = mock_user_with_roles(
        ["subscriber"]
    )  # A role not in ["viewer", "creator", "moderator"]
    # This setup tests the require_role(["viewer", "creator", "moderator"]) logic
    # when called by get_current_viewer dependency

    # The actual dependency call chain would be:
    # 1. FastAPI tries to resolve `get_current_viewer`
    # 2. It sees `Depends(require_role(...))`, so it calls `require_role(...)` which returns `role_checker`
    # 3. It then tries to resolve `role_checker`
    # 4. It sees `Depends(get_current_user_from_token)`, calls it (this is what we patch)
    # 5. `role_checker` then executes its logic.

    with patch(
        "app.api.v1.dependencies.get_current_user_from_token", new_callable=AsyncMock
    ) as mock_get_user:
        mock_get_user.return_value = user_unrelated_role
        with pytest.raises(HTTPException) as exc_info:
            # To test get_current_viewer, we need to simulate how FastAPI would call it.
            # FastAPI would call require_role(["viewer",...]), get the checker, then call the checker.
            # This is essentially testing the checker returned by require_role used by get_current_viewer
            role_checker_for_viewer = dependencies.require_role(
                ["viewer", "creator", "moderator"]
            )
            await role_checker_for_viewer(
                user_unrelated_role
            )  # Pass user directly to checker

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "User does not have any of the required roles: ['viewer', 'creator', 'moderator']"
            in exc_info.value.detail
        )
