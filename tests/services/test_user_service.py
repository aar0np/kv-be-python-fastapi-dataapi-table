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
        firstname="Test",
        lastname="User",
        email=f"testuser_{uuid4()}@example.com",  # Ensure unique email
        password="securepassword123",
    )


@pytest.mark.asyncio
async def test_get_user_by_email_from_credentials_table_found():
    mock_db_table = AsyncMock()
    expected_user_doc = {"email": "found@example.com", "firstname": "Found"}
    mock_db_table.find_one.return_value = expected_user_doc

    user_doc = await user_service.get_user_by_email_from_credentials_table(
        email="found@example.com", db_table=mock_db_table
    )

    mock_db_table.find_one.assert_called_once_with(
        filter={"email": "found@example.com"}
    )
    assert user_doc == expected_user_doc


@pytest.mark.asyncio
async def test_get_user_by_email_from_credentials_table_not_found():
    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = None  # Simulate user not found

    user_doc = await user_service.get_user_by_email_from_credentials_table(
        email="notfound@example.com", db_table=mock_db_table
    )

    mock_db_table.find_one.assert_called_once_with(
        filter={"email": "notfound@example.com"}
    )
    assert user_doc is None


@pytest.mark.asyncio
async def test_create_user_in_table(sample_user_create_request: UserCreateRequest):
    mock_users_table = AsyncMock()
    mock_credentials_table = AsyncMock()

    with patch("app.services.user_service.get_password_hash") as mock_get_password_hash:
        mock_hashed_password = "hashed_secure_password"
        mock_get_password_hash.return_value = mock_hashed_password

        test_user_id = uuid4()
        with patch("app.services.user_service.uuid4") as mock_uuid4:
            mock_uuid4.return_value = test_user_id

            created_user_doc = await user_service.create_user_in_table(
                user_in=sample_user_create_request,
                users_table=mock_users_table,
                credentials_table=mock_credentials_table,
            )

            mock_get_password_hash.assert_called_once_with(
                sample_user_create_request.password
            )
            mock_users_table.insert_one.assert_called_once()
            mock_credentials_table.insert_one.assert_called_once()

            # Check the user document
            args, kwargs = mock_users_table.insert_one.call_args
            user_document = kwargs.get("document")
            assert user_document is not None
            assert user_document["userid"] == str(test_user_id)
            assert user_document["firstname"] == sample_user_create_request.firstname
            assert user_document["lastname"] == sample_user_create_request.lastname
            assert user_document["email"] == sample_user_create_request.email
            assert user_document["account_status"] == "active"

            # Check the credentials document
            args, kwargs = mock_credentials_table.insert_one.call_args
            credentials_document = kwargs.get("document")
            assert credentials_document is not None
            assert credentials_document["email"] == sample_user_create_request.email
            assert credentials_document["password"] == mock_hashed_password
            assert credentials_document["userid"] == str(test_user_id)
            assert not credentials_document["account_locked"]

            # Verify the returned document
            assert created_user_doc["userid"] == test_user_id


@pytest.mark.asyncio
async def test_create_user_in_table_uses_get_table_if_no_db_table_provided(
    sample_user_create_request: UserCreateRequest,
):
    with patch(
        "app.services.user_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        mock_users_table = AsyncMock()
        mock_credentials_table = AsyncMock()
        mock_get_table.side_effect = [mock_users_table, mock_credentials_table]

        with patch(
            "app.services.user_service.get_password_hash", return_value="hashed"
        ):
            await user_service.create_user_in_table(user_in=sample_user_create_request)
            assert mock_get_table.call_count == 2
            mock_get_table.assert_any_call(user_service.USERS_TABLE_NAME)
            mock_get_table.assert_any_call(user_service.USER_CREDENTIALS_TABLE_NAME)
            mock_users_table.insert_one.assert_called_once()
            mock_credentials_table.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_email_uses_get_table_if_no_db_table_provided():
    with patch(
        "app.services.user_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        mock_actual_db_table = AsyncMock()
        mock_get_table.return_value = mock_actual_db_table
        mock_actual_db_table.find_one.return_value = None  # Example return

        await user_service.get_user_by_email_from_credentials_table(
            email="some@email.com"
        )
        mock_get_table.assert_called_once_with(user_service.USER_CREDENTIALS_TABLE_NAME)
        mock_actual_db_table.find_one.assert_called_once_with(
            filter={"email": "some@email.com"}
        )


# Tests for authenticate_user_from_table
@pytest.mark.asyncio
async def test_authenticate_user_from_table_success():
    email = "test@example.com"
    password = "correctpassword"
    user_id = uuid4()
    credentials_doc = {
        "email": email,
        "password": "hashed_correct_password",
        "userid": user_id,
        "account_locked": False,
    }
    user_doc = {
        "userid": user_id,
        "firstname": "Test",
        "lastname": "User",
        "email": email,
        "created_date": datetime.now(timezone.utc),
        "account_status": "active",
    }

    with (
        patch(
            "app.services.user_service.get_table",
            new_callable=AsyncMock,
        ) as mock_get_table,
        patch("app.services.user_service.verify_password") as mock_verify_password,
    ):
        mock_credentials_table = AsyncMock()
        mock_users_table = AsyncMock()
        mock_get_table.side_effect = [mock_credentials_table, mock_users_table]
        mock_credentials_table.find_one.return_value = credentials_doc
        mock_users_table.find_one.return_value = user_doc
        mock_verify_password.return_value = True

        authenticated_user = await user_service.authenticate_user_from_table(
            email, password
        )

        assert authenticated_user is not None
        assert isinstance(authenticated_user, User)
        assert authenticated_user.userid == user_id
        assert authenticated_user.email == email
        mock_verify_password.assert_called_once_with(
            password, "hashed_correct_password"
        )


@pytest.mark.asyncio
async def test_authenticate_user_from_table_user_not_found():
    email = "nonexistent@example.com"
    password = "anypassword"

    with patch(
        "app.services.user_service.get_table", new_callable=AsyncMock
    ) as mock_get_table:
        mock_credentials_table = AsyncMock()
        mock_get_table.return_value = mock_credentials_table
        mock_credentials_table.find_one.return_value = None

        authenticated_user = await user_service.authenticate_user_from_table(
            email, password
        )

        assert authenticated_user is None


@pytest.mark.asyncio
async def test_authenticate_user_from_table_incorrect_password():
    email = "test@example.com"
    password = "incorrectpassword"
    user_id = uuid4()
    credentials_doc = {
        "email": email,
        "password": "hashed_correct_password",
        "userid": user_id,
        "account_locked": False,
    }

    with (
        patch(
            "app.services.user_service.get_table",
            new_callable=AsyncMock,
        ) as mock_get_table,
        patch("app.services.user_service.verify_password") as mock_verify_password,
    ):
        mock_credentials_table = AsyncMock()
        mock_get_table.return_value = mock_credentials_table
        mock_credentials_table.find_one.return_value = credentials_doc
        mock_verify_password.return_value = False

        authenticated_user = await user_service.authenticate_user_from_table(
            email, password
        )

        assert authenticated_user is None
        mock_verify_password.assert_called_once_with(
            password, "hashed_correct_password"
        )


# --- Tests for update_user_in_table ---
@pytest.mark.asyncio
async def test_update_user_in_table_success():
    user_id = uuid4()
    update_request = UserProfileUpdateRequest(
        firstname="UpdatedFirstName", lastname="UpdatedLastName"
    )

    expected_updated_user_doc = {
        "userid": user_id,
        "firstname": "UpdatedFirstName",
        "lastname": "UpdatedLastName",
        "email": "test@example.com",
        "created_date": datetime.now(timezone.utc),
        "account_status": "active",
    }

    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = expected_updated_user_doc
    mock_db_table.update_one.return_value = MagicMock()

    updated_user = await user_service.update_user_in_table(
        user_id=user_id, update_data=update_request, db_table=mock_db_table
    )

    assert updated_user is not None
    assert updated_user.firstname == "UpdatedFirstName"
    assert updated_user.lastname == "UpdatedLastName"
    assert updated_user.email == "test@example.com"
    assert updated_user.userid == user_id

    mock_db_table.update_one.assert_called_once_with(
        filter={"userid": user_id},
        update={
            "$set": {"firstname": "UpdatedFirstName", "lastname": "UpdatedLastName"}
        },
    )


@pytest.mark.asyncio
async def test_update_user_in_table_no_fields_to_update():
    user_id = uuid4()
    update_request = UserProfileUpdateRequest()

    original_user_doc = {
        "userid": user_id,
        "firstname": "OriginalFirst",
        "lastname": "OriginalLast",
        "email": "test@example.com",
        "created_date": datetime.now(timezone.utc),
        "account_status": "active",
        "last_login_date": None,
    }

    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = original_user_doc

    with patch(
        "app.services.user_service.get_user_by_id_from_table",
        new_callable=AsyncMock,
    ) as mock_get_user_by_id:
        mock_get_user_by_id.return_value = User.model_validate(original_user_doc)

        updated_user = await user_service.update_user_in_table(
            user_id=user_id, update_data=update_request, db_table=mock_db_table
        )

        assert updated_user is not None
        assert updated_user.firstname == "OriginalFirst"
        assert updated_user.lastname == "OriginalLast"
        mock_db_table.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_in_table_user_not_found_initially():
    user_id = uuid4()
    update_request = UserProfileUpdateRequest(firstname="UpdatedName")

    mock_db_table = AsyncMock()
    mock_db_table.find_one.return_value = None

    updated_user = await user_service.update_user_in_table(
        user_id=user_id, update_data=update_request, db_table=mock_db_table
    )

    assert updated_user is None
    mock_db_table.update_one.assert_called_once_with(
        filter={"userid": user_id}, update={"$set": {"firstname": "UpdatedName"}}
    )
    mock_db_table.find_one.assert_called_once_with(filter={"userid": user_id})


@pytest.mark.asyncio
async def test_search_users_with_query():
    doc = {
        "userid": uuid4(),
        "firstname": "Alice",
        "lastname": "Smith",
        "email": "alice@example.com",
        "created_date": datetime.now(timezone.utc),
        "account_status": "active",
        "last_login_date": None,
    }

    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = [doc]
    mock_db.find.return_value = mock_cursor

    results = await user_service.search_users(query="alice", db_table=mock_db)

    mock_db.find.assert_called_once()
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_users_no_query():
    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = []
    mock_db.find.return_value = mock_cursor

    results = await user_service.search_users(db_table=mock_db)
    mock_db.find.assert_called_once()
    assert results == []
