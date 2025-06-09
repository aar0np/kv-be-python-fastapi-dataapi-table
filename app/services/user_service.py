from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime, timezone
import re
import inspect

# Legacy astrapy (<2) exposed AstraDBCollection in astrapy.db. Starting from
# v2 the equivalent type is `astrapy.AsyncCollection`.  The following logic
# tries the old import first and falls back to the new one, ultimately falling
# back to a simple stub when the real library is unavailable (e.g. in CI).

try:
    from astrapy.db import AstraDBCollection  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    try:
        from astrapy import AsyncCollection as AstraDBCollection  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - tests / CI without astrapy

        class AstraDBCollection:  # type: ignore
            async def find_one(self, *args, **kwargs):
                return None

            async def insert_one(self, *args, **kwargs):
                return {}

            async def update_one(self, *args, **kwargs):
                return {}

            # Additional helpers for list-based operations in unit tests/CI
            def find(self, *args, **kwargs):  # type: ignore[override]
                return []

            async def to_list(self, *args, **kwargs):  # noqa: D401
                return []

            async def count_documents(self, *args, **kwargs):  # noqa: D401
                return 0


from app.db.astra_client import get_table
from app.models.user import (
    UserCreateRequest,
    User,
    UserProfileUpdateRequest,
)
from app.core.security import get_password_hash, verify_password

USERS_TABLE_NAME: str = "users"
USER_CREDENTIALS_TABLE_NAME: str = "user_credentials"
LOGIN_ATTEMPTS_TABLE_NAME: str = "login_attempts"


async def get_user_by_email_from_credentials_table(
    email: str, db_table: Optional[AstraDBCollection] = None
) -> Optional[Dict[str, Any]]:
    table = (
        db_table
        if db_table is not None
        else await get_table(USER_CREDENTIALS_TABLE_NAME)
    )
    # Astrapy find_one returns None if not found, which matches our Optional[Dict] goal
    return await table.find_one(filter={"email": email})


async def create_user_in_table(
    user_in: UserCreateRequest,
    users_table: Optional[AstraDBCollection] = None,
    credentials_table: Optional[AstraDBCollection] = None,
) -> Dict[str, Any]:
    users_table = (
        users_table if users_table is not None else await get_table(USERS_TABLE_NAME)
    )
    credentials_table = (
        credentials_table
        if credentials_table is not None
        else await get_table(USER_CREDENTIALS_TABLE_NAME)
    )

    hashed_password = get_password_hash(user_in.password)
    user_id = uuid4()
    creation_date = datetime.now(timezone.utc)

    user_document: Dict[str, Any] = {
        "userid": user_id,
        "firstname": user_in.firstname,
        "lastname": user_in.lastname,
        "email": user_in.email,
        "created_date": creation_date,
        "account_status": "active",  # Default status
        "last_login_date": None,
    }

    credentials_document: Dict[str, Any] = {
        "email": user_in.email,
        "password": hashed_password,
        "userid": user_id,
        "account_locked": False,
    }

    await users_table.insert_one(document=user_document)
    await credentials_table.insert_one(document=credentials_document)

    # Return a dictionary that can be used for the UserCreateResponse
    return {
        "userid": user_id,
        "firstname": user_in.firstname,
        "lastname": user_in.lastname,
        "email": user_in.email,
    }


async def authenticate_user_from_table(
    email: str,
    password: str,
    users_table: Optional[AstraDBCollection] = None,
    credentials_table: Optional[AstraDBCollection] = None,
) -> Optional[User]:
    credentials_table = (
        credentials_table
        if credentials_table is not None
        else await get_table(USER_CREDENTIALS_TABLE_NAME)
    )
    user_credentials = await credentials_table.find_one(filter={"email": email})

    if not user_credentials:
        return None

    if not verify_password(password, user_credentials["password"]):
        # Here you would add logic to update the login_attempts table
        return None

    if user_credentials.get("account_locked"):
        return None  # Or raise an exception for locked account

    # Reset login attempts on successful login (logic to be added)

    users_table = (
        users_table if users_table is not None else await get_table(USERS_TABLE_NAME)
    )
    user_data_dict = await users_table.find_one(
        filter={"userid": user_credentials["userid"]}
    )

    if not user_data_dict:
        # This indicates a data consistency issue
        return None

    # Update last login date
    await users_table.update_one(
        filter={"userid": user_credentials["userid"]},
        update={"$set": {"last_login_date": datetime.now(timezone.utc)}},
    )

    # Map dictionary to User Pydantic model
    return User.model_validate(user_data_dict)


async def get_user_by_id_from_table(
    user_id: UUID, db_table: Optional[AstraDBCollection] = None
) -> Optional[User]:
    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)
    user_data_dict = await table.find_one(filter={"userid": user_id})

    if not user_data_dict:
        return None

    # Map dictionary to User Pydantic model
    return User.model_validate(user_data_dict)


async def update_user_in_table(
    user_id: UUID,
    update_data: UserProfileUpdateRequest,
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[User]:
    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    update_fields = update_data.model_dump(exclude_unset=True, by_alias=False)

    if not update_fields:  # No fields to update
        return await get_user_by_id_from_table(user_id=user_id, db_table=table)

    # Perform the update
    await table.update_one(filter={"userid": user_id}, update={"$set": update_fields})

    # Refetch the document to get the updated version
    updated_user_doc = await table.find_one(filter={"userid": user_id})
    if not updated_user_doc:
        return None

    # Map updated dictionary to User Pydantic model
    return User.model_validate(updated_user_doc)


async def search_users(
    query: Optional[str] = None,
    db_table: Optional[AstraDBCollection] = None,
    limit: int = 20,
) -> List[User]:
    """Search users by email or name (case-insensitive regex)."""

    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    query_filter: Dict[str, Any] = {}
    if query:
        escaped = re.escape(query)
        query_filter["$or"] = [
            {"email": {"$regex": escaped, "$options": "i"}},
            {"firstname": {"$regex": escaped, "$options": "i"}},
            {"lastname": {"$regex": escaped, "$options": "i"}},
        ]

    # ------------------------------------------------------------------
    # Retrieve matching documents – behave gracefully with both real Astra
    # collection cursors as well as various unittest.mock.AsyncMock setups.
    # ------------------------------------------------------------------

    result = table.find(filter=query_filter, limit=limit)

    docs: List[dict]

    if isinstance(result, list):
        # Tests may stub .find() to return a plain list already
        docs = result
    elif hasattr(result, "to_list"):
        # Official astrapy cursor as well as many mocks expose `.to_list()`
        docs = await result.to_list()  # type: ignore[attr-defined]
    elif inspect.isawaitable(result):
        # The call itself returned an awaitable (common with AsyncMock).  The
        # awaited value is typically a *cursor*-like object.  If that object
        # exposes `.to_list()` we invoke it, otherwise we try to treat it as a
        # sequence directly.

        awaited_obj = await result  # type: ignore[assignment]

        if hasattr(awaited_obj, "to_list"):
            docs = await awaited_obj.to_list()  # type: ignore[attr-defined]
        elif isinstance(awaited_obj, list):
            docs = awaited_obj
        else:
            docs = list(awaited_obj) if awaited_obj is not None else []
    else:
        # As a last resort, attempt to cast to list (could be iterable)
        docs = list(result) if result is not None else []

    return [User.model_validate(d) for d in docs]


# ---------------------------------------------------------------------------
# Role management stubs (used by moderation endpoints/tests)
# ---------------------------------------------------------------------------


async def assign_role_to_user(
    *,
    user: User,
    role: str,
    db_table: Optional[AstraDBCollection] = None,
) -> User:
    """Assign a role to a user (idempotent for the purpose of unit tests)."""

    if role in user.roles:
        return user  # Nothing to do

    user.roles.append(role)

    # Persist change if a real DB table is available; unit tests usually patch
    # this out, so we guard accordingly.
    if db_table is not None:
        await db_table.update_one(
            filter={"userid": user.userid},
            update={"$set": {"roles": user.roles}},
        )

    return user


async def revoke_role_from_user(
    *,
    user: User,
    role: str,
    db_table: Optional[AstraDBCollection] = None,
) -> User:
    """Remove a role from a user (idempotent)."""

    user.roles = [r for r in user.roles if r != role]

    if db_table is not None:
        await db_table.update_one(
            filter={"userid": user.userid},
            update={"$set": {"roles": user.roles}},
        )

    return user
