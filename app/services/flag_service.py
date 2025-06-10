from __future__ import annotations

"""Service layer handling creation and lifecycle of moderation flags."""

from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any  # noqa: F401
from uuid import UUID, uuid4
import inspect

from fastapi import HTTPException, status

from app.db.astra_client import AstraDBCollection, get_table
from app.models.flag import (
    FlagCreateRequest,
    Flag,
    ContentTypeEnum,
    FlagStatusEnum,
)
from app.models.user import User
from app.services import video_service
from app.services import comment_service

FLAGS_TABLE_NAME = "flags"


def _to_flag_model(doc: dict) -> Flag:
    """Convert DB document to `Flag` model instance."""

    return Flag(
        flagId=UUID(doc["flagId"]),
        userId=UUID(doc["userId"]),
        contentType=ContentTypeEnum(doc["contentType"]),
        contentId=UUID(doc["contentId"]),
        reasonCode=doc["reasonCode"],
        reasonText=doc.get("reasonText"),
        createdAt=doc["createdAt"],
        updatedAt=doc["updatedAt"],
        status=FlagStatusEnum(doc["status"]),
        moderatorId=UUID(doc["moderatorId"]) if doc.get("moderatorId") else None,
        moderatorNotes=doc.get("moderatorNotes"),
        resolvedAt=doc.get("resolvedAt"),
    )


async def create_flag(
    request: FlagCreateRequest,
    current_user: User,
    db_table: Optional[AstraDBCollection] = None,
) -> Flag:
    """Create a new moderation flag, validating content existence."""

    # Validate content existence via appropriate service.
    if request.contentType == ContentTypeEnum.VIDEO:
        content = await video_service.get_video_by_id(request.contentId)
    elif request.contentType == ContentTypeEnum.COMMENT:
        content = await comment_service.get_comment_by_id(request.contentId)
    else:  # pragma: no cover – extra safety
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type for flag",
        )

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{request.contentType.value.capitalize()} not found",
        )

    if db_table is None:
        db_table = await get_table(FLAGS_TABLE_NAME)

    now = datetime.now(timezone.utc)

    new_flag = Flag(
        flagId=uuid4(),
        userId=current_user.userId,
        contentType=request.contentType,
        contentId=request.contentId,
        reasonCode=request.reasonCode,
        reasonText=request.reasonText,
        createdAt=now,
        updatedAt=now,
        status=FlagStatusEnum.OPEN,
    )

    doc = new_flag.model_dump()
    # Convert UUIDs to strings for storage
    doc["flagId"] = str(doc["flagId"])
    doc["userId"] = str(doc["userId"])
    doc["contentId"] = str(doc["contentId"])

    await db_table.insert_one(document=doc)

    return new_flag


async def list_flags(
    *,
    page: int,
    page_size: int,
    status_filter: Optional[FlagStatusEnum] = None,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[Flag], int]:
    """Return paginated flags for moderators with optional status filter."""

    if db_table is None:
        db_table = await get_table(FLAGS_TABLE_NAME)

    query_filter: Dict[str, Any] = {}
    if status_filter is not None:
        query_filter["status"] = status_filter.value

    skip = (page - 1) * page_size

    # ------------------------------------------------------------------
    # Gracefully handle the scenario where the **flags** collection has not
    # been created yet.  Astra will raise a ``DataAPIResponseException`` with
    # code ``COLLECTION_NOT_EXIST`` when attempting to query a missing
    # collection.  Instead of propagating the 500 error to the client we
    # treat this as "no results" so that the moderation inbox simply renders
    # an empty list until the first flag is created (which implicitly creates
    # the collection).
    # ------------------------------------------------------------------

    try:
        cursor = db_table.find(
            filter=query_filter,
            skip=skip,
            limit=page_size,
            sort={"createdAt": -1},
        )

        raw_docs = cursor.to_list() if hasattr(cursor, "to_list") else cursor
        docs = await raw_docs if inspect.isawaitable(raw_docs) else raw_docs

        try:
            total_items = await db_table.count_documents(
                filter=query_filter, upper_bound=10**9
            )
        except TypeError:
            # Stub collections used in tests don't accept ``upper_bound``.
            total_items = await db_table.count_documents(filter=query_filter)

    except Exception as exc:
        # Import locally to avoid an unconditional dependency when running in
        # environments without the real Astra client (CI).
        from astrapy.exceptions.data_api_exceptions import DataAPIResponseException

        if isinstance(exc, DataAPIResponseException) and "COLLECTION_NOT_EXIST" in str(exc):
            # Collection hasn't been created yet → treat as empty result set.
            return [], 0
        # Bubble up any other unexpected errors.
        raise

    return [_to_flag_model(d) for d in docs], total_items


async def get_flag_by_id(
    *, flag_id: UUID, db_table: Optional[AstraDBCollection] = None
) -> Optional[Flag]:
    if db_table is None:
        db_table = await get_table(FLAGS_TABLE_NAME)

    doc = await db_table.find_one(filter={"flagId": str(flag_id)})
    if doc is None:
        return None
    return _to_flag_model(doc)


async def action_on_flag(
    *,
    flag_to_action: Flag,
    new_status: FlagStatusEnum,
    moderator_notes: Optional[str],
    moderator: User,
    db_table: Optional[AstraDBCollection] = None,
) -> Flag:
    """Update the status/notes of a flag and return updated object."""

    if db_table is None:
        db_table = await get_table(FLAGS_TABLE_NAME)

    now = datetime.now(timezone.utc)

    update_payload_db: Dict[str, Any] = {
        "status": new_status.value,
        "moderatorId": str(moderator.userId),
        "updatedAt": now,
        "resolvedAt": now
        if new_status in {FlagStatusEnum.APPROVED, FlagStatusEnum.REJECTED}
        else None,
        "moderatorNotes": moderator_notes,
    }

    update_payload_db = {k: v for k, v in update_payload_db.items() if v is not None}

    await db_table.update_one(
        filter={"flagId": str(flag_to_action.flagId)},
        update={"$set": update_payload_db},
    )

    # TODO stub as above
    if new_status == FlagStatusEnum.APPROVED:
        print(
            f"STUB: Flag {flag_to_action.flagId} approved. TODO: take action on content {flag_to_action.contentType} ID {flag_to_action.contentId}."
        )

    update_payload_model = {
        **{k: v for k, v in update_payload_db.items() if k != "moderatorId"},
        "moderatorId": moderator.userId,
    }

    return flag_to_action.model_copy(update=update_payload_model)
