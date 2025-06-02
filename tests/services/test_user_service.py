import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services import user_service
from app.models.user import UserCreateRequest, User, UserProfileUpdateRequest


# Fixture for a sample UserCreateRequest
@pytest.fixture
def sample_user_create_request() -> UserCreateRequest:
    return UserCreateRequest(
        firstName="Test",
        lastName="User",
        email=f"testuser_{uuid4()}@example.com",  # Ensure unique email
        password="securepassword123",
    )


@pytest.mark.asyncio
async def test_get_user_by_email_from_table_found():
    mock_db_table = AsyncMock()
    expected_user_doc = {"email": "found@example.com", "firstName": "Found"}
    mock_db_table.find_one.return_value = expected_user_doc

    user_doc = await user_service.get_user_by_email_from_table(
        email="found@example.com", db_table=mock_db_table
    )

    mock_db_table.find_one.assert_called_once_with(
        filter={"email": "found@example.com"}
    )
    assert user_doc == expected_user_doc


@pytest.mark.asyncio
async def test_get_user_by_email_from_table_not_found():
    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = None  # Simulate user not found

    user_doc = await user_service.get_user_by_email_from_table(
        email="notfound@example.com", db_table=mock_db_table
    )

    mock_db_table.find_one.assert_called_once_with(
        filter={"email": "notfound@example.com"}
    )
    assert user_doc is None


@pytest.mark.asyncio
async def test_create_user_in_table(sample_user_create_request: UserCreateRequest):
    mock_db_table = AsyncMock()
    # Mock insert_one to simulate successful insertion by AstraDB
    # AstraDB insert_one typically returns a dict like {"insertedIds": ["some_id"]}
    # For this test, we only care that it's called and what it's called with.
    # The service function returns the input document, so we don't need to mock a specific return value for insert_one here for that part.
    mock_db_table.insert_one.return_value = MagicMock(inserted_id=str(uuid4()))

    with patch("app.services.user_service.get_password_hash") as mock_get_password_hash:
        mock_hashed_password = "hashed_secure_password"
        mock_get_password_hash.return_value = mock_hashed_password

        # Patch uuid4 to control the generated userid for assertion
        test_user_id = uuid4()
        with patch("app.services.user_service.uuid4") as mock_uuid4:
            mock_uuid4.return_value = test_user_id

            created_user_doc = await user_service.create_user_in_table(
                user_in=sample_user_create_request, db_table=mock_db_table
            )

            mock_get_password_hash.assert_called_once_with(
                sample_user_create_request.password
            )
            mock_db_table.insert_one.assert_called_once()

            # Check the document structure passed to insert_one
            args, kwargs = mock_db_table.insert_one.call_args
            inserted_document = kwargs.get("document")

            assert inserted_document is not None
            assert inserted_document["userid"] == str(test_user_id)
            assert (
                inserted_document["firstName"] == sample_user_create_request.firstName
            )
            assert inserted_document["lastName"] == sample_user_create_request.lastName
            assert inserted_document["email"] == sample_user_create_request.email
            assert inserted_document["hashed_password"] == mock_hashed_password
            assert inserted_document["roles"] == ["viewer"]
            assert isinstance(inserted_document["created_at"], datetime)
            assert inserted_document["created_at"].tzinfo == timezone.utc

            # Verify the returned document is what we expect (the one passed to insert_one)
            assert created_user_doc == inserted_document


@pytest.mark.asyncio
async def test_create_user_in_table_uses_get_table_if_no_db_table_provided(
    sample_user_create_request: UserCreateRequest,
):
    with patch(
        "app.services.user_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        mock_actual_db_table = AsyncMock()
        mock_get_table.return_value = mock_actual_db_table
        mock_actual_db_table.insert_one.return_value = MagicMock(
            inserted_id=str(uuid4())
        )

        with patch(
            "app.services.user_service.get_password_hash", return_value="hashed"
        ):
            await user_service.create_user_in_table(user_in=sample_user_create_request)
            mock_get_table.assert_called_once_with(user_service.USERS_TABLE_NAME)
            mock_actual_db_table.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_email_uses_get_table_if_no_db_table_provided():
    with patch(
        "app.services.user_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        mock_actual_db_table = AsyncMock()
        mock_get_table.return_value = mock_actual_db_table
        mock_actual_db_table.find_one.return_value = None  # Example return

        await user_service.get_user_by_email_from_table(email="some@email.com")
        mock_get_table.assert_called_once_with(user_service.USERS_TABLE_NAME)
        mock_actual_db_table.find_one.assert_called_once_with(
            filter={"email": "some@email.com"}
        )


# Tests for authenticate_user_from_table
@pytest.mark.asyncio
async def test_authenticate_user_from_table_success():
    email = "test@example.com"
    password = "correctpassword"
    user_id = uuid4()
    db_user_doc = {
        "userid": str(user_id),
        "firstName": "Test",
        "lastName": "User",
        "email": email,
        "hashed_password": "hashed_correct_password",  # Assume this is the hash of "correctpassword"
        "roles": ["viewer"],
    }

    with (
        patch(
            "app.services.user_service.get_user_by_email_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user_by_email,
        patch("app.services.user_service.verify_password") as mock_verify_password,
    ):
        mock_get_user_by_email.return_value = db_user_doc
        mock_verify_password.return_value = True

        authenticated_user = await user_service.authenticate_user_from_table(
            email, password
        )

        assert authenticated_user is not None
        assert isinstance(authenticated_user, User)
        assert authenticated_user.userId == user_id
        assert authenticated_user.email == email
        assert authenticated_user.roles == ["viewer"]
        mock_get_user_by_email.assert_called_once_with(email, None)  # None for db_table
        mock_verify_password.assert_called_once_with(
            password, "hashed_correct_password"
        )


@pytest.mark.asyncio
async def test_authenticate_user_from_table_user_not_found():
    email = "nonexistent@example.com"
    password = "anypassword"

    with patch(
        "app.services.user_service.get_user_by_email_from_table", new_callable=AsyncMock
    ) as mock_get_user_by_email:
        mock_get_user_by_email.return_value = None  # Simulate user not found

        authenticated_user = await user_service.authenticate_user_from_table(
            email, password
        )

        assert authenticated_user is None
        mock_get_user_by_email.assert_called_once_with(email, None)


@pytest.mark.asyncio
async def test_authenticate_user_from_table_incorrect_password():
    email = "test@example.com"
    password = "incorrectpassword"
    user_id = uuid4()
    db_user_doc = {
        "userid": str(user_id),
        "firstName": "Test",
        "lastName": "User",
        "email": email,
        "hashed_password": "hashed_correct_password",
        "roles": ["viewer"],
    }

    with (
        patch(
            "app.services.user_service.get_user_by_email_from_table",
            new_callable=AsyncMock,
        ) as mock_get_user_by_email,
        patch("app.services.user_service.verify_password") as mock_verify_password,
    ):
        mock_get_user_by_email.return_value = db_user_doc
        mock_verify_password.return_value = False  # Simulate incorrect password

        authenticated_user = await user_service.authenticate_user_from_table(
            email, password
        )

        assert authenticated_user is None
        mock_get_user_by_email.assert_called_once_with(email, None)
        mock_verify_password.assert_called_once_with(
            password, "hashed_correct_password"
        )


# --- Tests for update_user_in_table ---
@pytest.mark.asyncio
async def test_update_user_in_table_success():
    user_id = uuid4()
    update_request = UserProfileUpdateRequest(
        firstName="UpdatedFirstName", lastName="UpdatedLastName"
    )

    original_user_doc = {
        "userid": str(user_id),
        "firstName": "OriginalFirst",
        "lastName": "OriginalLast",
        "email": "test@example.com",
        "hashed_password": "somehash",
        "roles": ["viewer"],
    }
    # This is what we expect find_one to return *after* the update
    expected_updated_user_doc = {
        "userid": str(user_id),
        "firstName": "UpdatedFirstName",  # Updated
        "lastName": "UpdatedLastName",  # Updated
        "email": "test@example.com",  # Unchanged
        "hashed_password": "somehash",  # Unchanged
        "roles": ["viewer"],  # Unchanged
    }

    mock_db_table = AsyncMock()
    # find_one will be called twice: first to check existence, second to get updated doc
    mock_db_table.find_one.side_effect = [original_user_doc, expected_updated_user_doc]
    mock_db_table.update_one.return_value = (
        MagicMock()
    )  # Assume update_one returns some result object

    updated_user = await user_service.update_user_in_table(
        user_id=user_id, update_data=update_request, db_table=mock_db_table
    )

    assert updated_user is not None
    assert updated_user.firstName == "UpdatedFirstName"
    assert updated_user.lastName == "UpdatedLastName"
    assert updated_user.email == "test@example.com"
    assert updated_user.userId == user_id

    assert mock_db_table.find_one.call_count == 2
    mock_db_table.find_one.assert_any_call(filter={"userid": str(user_id)})
    mock_db_table.update_one.assert_called_once_with(
        filter={"userid": str(user_id)},
        update={
            "$set": {"firstName": "UpdatedFirstName", "lastName": "UpdatedLastName"}
        },
    )


@pytest.mark.asyncio
async def test_update_user_in_table_no_fields_to_update():
    user_id = uuid4()
    update_request = UserProfileUpdateRequest()  # Empty update request

    original_user_doc = {
        "userid": str(user_id),
        "firstName": "OriginalFirst",
        "lastName": "OriginalLast",
        "email": "test@example.com",
        "roles": ["viewer"],
    }

    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = original_user_doc  # find_one called once

    updated_user = await user_service.update_user_in_table(
        user_id=user_id, update_data=update_request, db_table=mock_db_table
    )

    assert updated_user is not None
    assert updated_user.firstName == "OriginalFirst"
    assert updated_user.lastName == "OriginalLast"
    mock_db_table.find_one.assert_called_once_with(filter={"userid": str(user_id)})
    mock_db_table.update_one.assert_not_called()  # update_one should not be called


@pytest.mark.asyncio
async def test_update_user_in_table_user_not_found_initially():
    user_id = uuid4()
    update_request = UserProfileUpdateRequest(firstName="UpdatedName")

    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = None  # Simulate user not found on first call

    updated_user = await user_service.update_user_in_table(
        user_id=user_id, update_data=update_request, db_table=mock_db_table
    )

    assert updated_user is None
    mock_db_table.find_one.assert_called_once_with(filter={"userid": str(user_id)})
    mock_db_table.update_one.assert_not_called()


# --- Tests for role assignment and revocation ---

@pytest.mark.asyncio
async def test_assign_role_to_user_adds_role():
    user_id = uuid4()
    initial_doc = {
        "userid": str(user_id),
        "firstName": "First",
        "lastName": "Last",
        "email": "a@b.com",
        "roles": ["viewer"],
    }
    updated_doc = {**initial_doc, "roles": ["viewer", "moderator"]}

    mock_db = AsyncMock()
    mock_db.find_one.side_effect = [initial_doc, updated_doc]
    mock_db.update_one.return_value = MagicMock()

    updated_user = await user_service.assign_role_to_user(
        user_to_modify_id=user_id, role_to_assign="moderator", db_table=mock_db
    )

    # Ensure update_one called with roles plus moderator
    mock_db.update_one.assert_called_once_with(
        filter={"userid": str(user_id)}, update={"$set": {"roles": ["viewer", "moderator"]}}
    )
    assert updated_user is not None and "moderator" in updated_user.roles


@pytest.mark.asyncio
async def test_revoke_role_from_user_removes_role():
    user_id = uuid4()
    initial_doc = {
        "userid": str(user_id),
        "firstName": "First",
        "lastName": "Last",
        "email": "a@b.com",
        "roles": ["viewer", "moderator"],
    }
    updated_doc = {**initial_doc, "roles": ["viewer"]}

    mock_db = AsyncMock()
    mock_db.find_one.side_effect = [initial_doc, updated_doc]
    mock_db.update_one.return_value = MagicMock()

    updated_user = await user_service.revoke_role_from_user(
        user_to_modify_id=user_id, role_to_revoke="moderator", db_table=mock_db
    )

    mock_db.update_one.assert_called_once_with(
        filter={"userid": str(user_id)}, update={"$set": {"roles": ["viewer"]}}
    )
    assert updated_user is not None and "moderator" not in updated_user.roles
