from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime, timezone
import re

from astrapy.db import AstraDBCollection

from app.db.astra_client import get_table
from app.models.user import UserCreateRequest, User, UserProfileUpdateRequest
from app.core.security import get_password_hash, verify_password

USERS_TABLE_NAME: str = "users"


async def get_user_by_email_from_table(
    email: str, db_table: Optional[AstraDBCollection] = None
) -> Optional[Dict[str, Any]]:
    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)
    # Astrapy find_one returns None if not found, which matches our Optional[Dict] goal
    return await table.find_one(filter={"email": email})


async def create_user_in_table(
    user_in: UserCreateRequest, db_table: Optional[AstraDBCollection] = None
) -> Dict[str, Any]:
    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    hashed_password = get_password_hash(user_in.password)
    user_id = uuid4()

    user_document: Dict[str, Any] = {
        "userid": str(user_id),  # Store UUID as string in DB
        "firstName": user_in.firstName,
        "lastName": user_in.lastName,
        "email": user_in.email,
        "hashed_password": hashed_password,
        "roles": ["viewer"],  # Default role
        "created_at": datetime.now(timezone.utc),
    }

    # astrapy's insert_one returns an object with an inserted_id or similar.
    # For now, we assume it raises an exception on failure. The prompt asks us
    # to return the user_document itself. If insert_one provides more/different info,
    # this might need adjustment based on astrapy behavior.
    await table.insert_one(document=user_document)
    # Consider logging insert_result.inserted_id for debugging if needed

    # Ensure the returned document has a stringified userId for consistency if needed later,
    # but the document being inserted already has `userid` as str(uuid4()).
    # The prompt asks to return the created user document.
    return user_document


async def authenticate_user_from_table(
    email: str, password: str, db_table: Optional[AstraDBCollection] = None
) -> Optional[User]:
    user_data_dict = await get_user_by_email_from_table(email, db_table)

    if not user_data_dict:
        return None

    if not verify_password(password, user_data_dict["hashed_password"]):
        return None

    # Map dictionary to User Pydantic model
    # Ensure all fields are correctly mapped, especially userId from userid
    return User(
        userId=UUID(user_data_dict["userid"]),
        firstName=user_data_dict["firstName"],
        lastName=user_data_dict["lastName"],
        email=user_data_dict["email"],
        roles=user_data_dict.get("roles", ["viewer"]),  # Default if roles not in DB
    )


async def get_user_by_id_from_table(
    user_id: UUID, db_table: Optional[AstraDBCollection] = None
) -> Optional[User]:
    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)
    user_data_dict = await table.find_one(filter={"userid": str(user_id)})

    if not user_data_dict:
        return None

    # Map dictionary to User Pydantic model
    return User(
        userId=UUID(
            user_data_dict["userid"]
        ),  # Already a UUID, but ensure it's from the doc
        firstName=user_data_dict["firstName"],
        lastName=user_data_dict["lastName"],
        email=user_data_dict["email"],
        roles=user_data_dict.get("roles", ["viewer"]),  # Default if roles not in DB
    )


async def update_user_in_table(
    user_id: UUID,
    update_data: UserProfileUpdateRequest,
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[User]:
    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    # Fetch the current user document to ensure it exists and for full data return
    # While not strictly necessary if update_one handles non-existent docs gracefully,
    # it's good practice for services to confirm existence before update if returning the object.
    current_user_doc = await table.find_one(filter={"userid": str(user_id)})
    if not current_user_doc:
        return None  # User not found

    update_fields = update_data.model_dump(
        exclude_unset=True
    )  # Get only provided fields

    if not update_fields:  # No fields to update
        # Return the current user data mapped to User model
        return User(
            userId=UUID(current_user_doc["userid"]),
            firstName=current_user_doc["firstName"],
            lastName=current_user_doc["lastName"],
            email=current_user_doc["email"],
            roles=current_user_doc.get("roles", ["viewer"]),
        )

    # Perform the update
    # Astrapy's update_one might have specific return values (e.g., update result object)
    # We need to ensure we fetch the *updated* document to return.
    await table.update_one(
        filter={"userid": str(user_id)}, update={"$set": update_fields}
    )

    # Refetch the document to get the updated version
    updated_user_doc = await table.find_one(filter={"userid": str(user_id)})
    if not updated_user_doc:  # Should not happen if update was on existing user
        # This case implies the user was deleted between the update and refetch, or an issue with DB consistency.
        # Log an error or handle as appropriate for your application's guarantees.
        # For now, as per prompt, if initial fetch found user, update is assumed to succeed on existing doc.
        return None

    # Map updated dictionary to User Pydantic model
    return User(
        userId=UUID(updated_user_doc["userid"]),
        firstName=updated_user_doc["firstName"],
        lastName=updated_user_doc["lastName"],
        email=updated_user_doc["email"],
        roles=updated_user_doc.get("roles", ["viewer"]),
    )


# ---------------------------------------------------------------------------
# Role management helpers (moderator, creator, etc.)
# ---------------------------------------------------------------------------


async def _update_user_roles(
    *,
    user_id: UUID,
    new_roles: List[str],
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[User]:
    """Helper to persist updated roles list and return the fresh `User` object."""

    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    await table.update_one(
        filter={"userid": str(user_id)},
        update={"$set": {"roles": new_roles}},
    )

    # Fetch updated doc
    updated_doc = await table.find_one(filter={"userid": str(user_id)})
    if updated_doc is None:
        return None

    return User(
        userId=user_id,
        firstName=updated_doc["firstName"],
        lastName=updated_doc["lastName"],
        email=updated_doc["email"],
        roles=updated_doc.get("roles", ["viewer"]),
    )


async def assign_role_to_user(
    user_to_modify_id: UUID,
    role_to_assign: str,
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[User]:
    """Append a role to the user's role list if not already present."""

    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    user_doc = await table.find_one(filter={"userid": str(user_to_modify_id)})
    if user_doc is None:
        return None

    roles: List[str] = user_doc.get("roles", ["viewer"])
    if role_to_assign not in roles:
        roles.append(role_to_assign)
        return await _update_user_roles(
            user_id=user_to_modify_id, new_roles=roles, db_table=table
        )

    # Role already present — simply return current user model
    return User(
        userId=user_to_modify_id,
        firstName=user_doc["firstName"],
        lastName=user_doc["lastName"],
        email=user_doc["email"],
        roles=roles,
    )


async def revoke_role_from_user(
    user_to_modify_id: UUID,
    role_to_revoke: str,
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[User]:
    """Remove a role from the user's role list; no-op if role absent."""

    table = db_table if db_table is not None else await get_table(USERS_TABLE_NAME)

    user_doc = await table.find_one(filter={"userid": str(user_to_modify_id)})
    if user_doc is None:
        return None

    roles: List[str] = user_doc.get("roles", ["viewer"])

    if role_to_revoke in roles:
        roles.remove(role_to_revoke)
        return await _update_user_roles(
            user_id=user_to_modify_id, new_roles=roles, db_table=table
        )

    # Role not present — return current user model
    return User(
        userId=user_to_modify_id,
        firstName=user_doc["firstName"],
        lastName=user_doc["lastName"],
        email=user_doc["email"],
        roles=roles,
    )


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
            {"firstName": {"$regex": escaped, "$options": "i"}},
            {"lastName": {"$regex": escaped, "$options": "i"}},
        ]

    cursor = table.find(filter=query_filter, limit=limit)
    docs = await cursor.to_list(length=limit) if hasattr(cursor, "to_list") else cursor

    return [
        User(
            userId=UUID(d["userid"]),
            firstName=d["firstName"],
            lastName=d["lastName"],
            email=d["email"],
            roles=d.get("roles", ["viewer"]),
        )
        for d in docs
    ]
