import pytest
from app.core.security import (
    get_password_hash,
    verify_password,
    pwd_context,
    create_access_token,
    TokenPayload,
    settings,
)
from datetime import datetime, timedelta, timezone
from jose import jwt
from uuid import uuid4


def test_get_password_hash():
    password = "testpassword123"
    hashed_password = get_password_hash(password)
    assert hashed_password is not None
    assert password != hashed_password  # Ensure it's not storing plain text
    # Check if the hash uses the configured scheme (bcrypt)
    assert pwd_context.identify(hashed_password) == "bcrypt"


def test_verify_password_correct():
    password = "testpassword123"
    hashed_password = get_password_hash(password)
    assert verify_password(password, hashed_password) is True


def test_verify_password_incorrect():
    password = "testpassword123"
    wrong_password = "wrongpassword456"
    hashed_password = get_password_hash(password)
    assert verify_password(wrong_password, hashed_password) is False


def test_verify_password_with_tampered_hash():
    password = "testpassword123"
    hashed_password = get_password_hash(password)
    # Tamper the hash slightly (e.g., change a character)
    # This assumes standard bcrypt hash structure; robust tampering is complex.
    # A simple change should suffice for this test's purpose.
    if (
        len(hashed_password) > 10
    ):  # Basic check to avoid error on unexpectedly short hash
        tampered_hash = list(hashed_password)
        original_char_index = -5  # pick a char towards the end
        original_char = tampered_hash[original_char_index]
        # Change it to something else, ensuring it is different
        tampered_hash[original_char_index] = (
            chr(ord(original_char) + 1) if original_char != "z" else "a"
        )
        tampered_hash_str = "".join(tampered_hash)
        try:
            assert verify_password(password, tampered_hash_str) is False
        except ValueError:
            # Newer passlib may raise for invalid hash content
            pass
    else:
        # Skip if hash is too short to tamper reliably for this test
        pytest.skip("Hashed password too short to reliably tamper for this test")


def test_create_access_token_default_expiry():
    user_id = uuid4()
    roles = ["viewer"]
    token = create_access_token(subject=user_id, roles=roles)
    assert token is not None
    assert isinstance(token, str)

    # Decode token to check payload (optional, but good for verification)
    try:
        payload_dict = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        payload = TokenPayload(**payload_dict)
        assert str(payload.sub) == str(user_id)
        assert payload.roles == roles
        assert payload.exp is not None
        # Check if expiry is roughly ACCESS_TOKEN_EXPIRE_MINUTES from now
        expected_exp = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        # Allow a small delta for processing time (e.g., 5 seconds)
        assert abs((payload.exp - expected_exp).total_seconds()) < 5
    except jwt.JWTError as e:
        pytest.fail(f"JWT decoding failed: {e}")


def test_create_access_token_custom_expiry():
    user_id = uuid4()
    roles = ["creator"]
    custom_delta = timedelta(hours=1)
    token = create_access_token(
        subject=user_id, roles=roles, expires_delta=custom_delta
    )
    assert token is not None

    try:
        payload_dict = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        payload = TokenPayload(**payload_dict)
        assert str(payload.sub) == str(user_id)
        assert payload.roles == roles
        assert payload.exp is not None
        expected_exp = datetime.now(timezone.utc) + custom_delta
        assert abs((payload.exp - expected_exp).total_seconds()) < 5
    except jwt.JWTError as e:
        pytest.fail(f"JWT decoding failed: {e}")
