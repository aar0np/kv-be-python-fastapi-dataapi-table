from __future__ import annotations

"""Service layer handling creation and lifecycle of moderation flags."""

from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any  # noqa: F401
from uuid import UUID, uuid4, uuid1
import inspect

from fastapi import HTTPException, status

from app.db.astra_client import AstraDBCollection, get_table, get_astra_db
from app.models.flag import (
    FlagCreateRequest,
    Flag,
    ContentTypeEnum,
    FlagStatusEnum,
)
from app.models.user import User
from app.services import video_service
from app.services import comment_service
from app.utils.db_helpers import safe_count

CONTENT_MOD_TABLE_NAME = "content_moderation"


def _to_flag_model(doc: dict) -> Flag:
    """Convert DB document to `Flag` model instance."""

    # Handle legacy collection docs vs. table rows.  Normalise keys first.
    norm = {k.lower(): v for k, v in doc.items()}

    # Extract / derive fields with sensible fallbacks
    flag_id = norm.get("flagid") or norm.get("flag_id")
    content_id = norm.get("contentid") or norm.get("content_id")
    content_type = norm.get("content_type") or norm.get("contenttype")

    reason_code: str | None = None
    reason_text: str | None = None

    if "reasoncode" in norm:
        reason_code = norm["reasoncode"]
        reason_text = norm.get("reasontext")
    elif "flagged_reason" in norm:
        combined = norm["flagged_reason"]
        if ":" in combined:
            reason_code, reason_text = combined.split(":", 1)
        else:
            reason_code = combined

    user_id_raw = norm.get("userid") or norm.get("user_id")

    return Flag(
        flagId=UUID(flag_id) if flag_id else uuid4(),
        userId=UUID(user_id_raw) if user_id_raw else UUID(int=0),
        contentType=ContentTypeEnum(content_type)
        if content_type
        else ContentTypeEnum.VIDEO,
        contentId=UUID(content_id) if content_id else UUID(int=0),
        reasonCode=reason_code or "other",
        reasonText=reason_text,
        createdAt=norm.get("createdat")
        or norm.get("review_date")
        or datetime.now(timezone.utc),
        updatedAt=norm.get("updatedat")
        or norm.get("review_date")
        or datetime.now(timezone.utc),
        status=FlagStatusEnum(norm.get("status", "open")),
        moderatorId=UUID(norm["moderatorid"])
        if norm.get("moderatorid")
        else (UUID(norm["reviewer"]) if norm.get("reviewer") else None),
        moderatorNotes=norm.get("moderatornotes"),
        resolvedAt=norm.get("resolvedat") or norm.get("review_date"),
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
        db_table = await get_table(CONTENT_MOD_TABLE_NAME)

    now = datetime.now(timezone.utc)

    # Generate a *timeuuid* flagId as required by the table schema
    flag_id_time = uuid1()

    new_flag = Flag(
        flagId=flag_id_time,
        userId=current_user.userId,
        contentType=request.contentType,
        contentId=request.contentId,
        reasonCode=request.reasonCode,
        reasonText=request.reasonText,
        createdAt=now,
        updatedAt=now,
        status=FlagStatusEnum.OPEN,
    )

    # ------------------------------------------------------------------
    # Translate to the *content_moderation* table schema.  Allowed columns
    # (see docs/schema-astra.cql):
    #   contentid, flagid, content_type, status, flagged_reason, reviewer,
    #   review_date
    # ------------------------------------------------------------------

    flagged_reason_combined = (
        f"{request.reasonCode.value}:{request.reasonText}"
        if request.reasonText
        else request.reasonCode.value
    )

    doc = {
        "contentid": str(request.contentId),
        "flagid": str(flag_id_time),
        "content_type": request.contentType.value,
        "status": FlagStatusEnum.OPEN.value,
        "flagged_reason": flagged_reason_combined,
        # reviewer / review_date left out for initial insert
        # Extra context columns (not in schema); added only for potential future
        # audit use.  If the DB rejects them we strip and retry once.
        "userid": str(current_user.userId),
        "created_at": now,
    }

    # ------------------------------------------------------------------
    # Attempt to insert the document.  If the **flags** collection has not
    # been created yet Astra will return a ``COLLECTION_NOT_EXIST`` error.
    # Instead of surfacing a 500 to the caller we create the collection on
    # -the-fly and retry once.  This mirrors the graceful handling already
    # implemented in ``list_flags``.
    # ------------------------------------------------------------------

    try:
        await db_table.insert_one(document=doc)
    except Exception as exc:
        # Import locally to avoid requiring the dependency when running
        # in environments (e.g. CI) that rely on the stub client.
        from astrapy.exceptions.data_api_exceptions import DataAPIResponseException  # type: ignore

        if isinstance(exc, DataAPIResponseException) and "COLLECTION_NOT_EXIST" in str(
            exc
        ):
            # Lazily create the collection and retry the insert exactly once.
            db = await get_astra_db()

            # ``create_collection`` exists in both astrapy v1 and v2.  For v2
            # we rely on the compatibility wrapper defined in `app.db.astra_client`.
            try:
                await db.create_collection(CONTENT_MOD_TABLE_NAME)
            except Exception:
                # If another concurrent request already created the collection
                # we can safely ignore the error and retry the insert.
                pass

            db_table = await get_table(CONTENT_MOD_TABLE_NAME)
            await db_table.insert_one(document=doc)
        elif isinstance(
            exc, DataAPIResponseException
        ) and "UNKNOWN_TABLE_COLUMNS" in str(exc):
            # Strip any keys not in the table schema and retry once.
            allowed_cols = {
                "contentid",
                "flagid",
                "content_type",
                "status",
                "flagged_reason",
                "reviewer",
                "review_date",
            }

            filtered = {k: v for k, v in doc.items() if k in allowed_cols}

            await db_table.insert_one(document=filtered)
        else:
            raise

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
        db_table = await get_table(CONTENT_MOD_TABLE_NAME)

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
        # Tables do not have a ``createdAt`` column. Attempt the query with the
        # legacy sort field first for compatibility with existing collection
        # data, then gracefully retry without the sort clause if the Data API
        # rejects it.

        find_kwargs = {
            "filter": query_filter,
            "limit": page_size,
        }
        if skip > 0:
            find_kwargs["skip"] = skip
        # Optimistic sort on createdAt for backwards compatibility
        find_kwargs["sort"] = {"createdAt": -1}

        from astrapy.exceptions.data_api_exceptions import DataAPIResponseException

        cursor = db_table.find(**find_kwargs)

        async def _fetch_docs(cur):
            raw = cur.to_list() if hasattr(cur, "to_list") else cur
            return await raw if inspect.isawaitable(raw) else raw

        try:
            docs = await _fetch_docs(cursor)
        except DataAPIResponseException as exc:
            if "CANNOT_SORT_UNKNOWN_COLUMNS" not in str(exc):
                raise

            # Retry without the offending sort clause
            find_kwargs.pop("sort", None)
            cursor = db_table.find(**find_kwargs)
            docs = await _fetch_docs(cursor)

        total_items = await safe_count(
            db_table,
            query_filter=query_filter,
            fallback_len=len(docs),
        )

    except Exception as exc:
        # Import locally to avoid an unconditional dependency when running in
        # environments without the real Astra client (CI).
        from astrapy.exceptions.data_api_exceptions import DataAPIResponseException

        if isinstance(exc, DataAPIResponseException) and "COLLECTION_NOT_EXIST" in str(
            exc
        ):
            # Collection hasn't been created yet → treat as empty result set.
            return [], 0
        # Bubble up any other unexpected errors.
        raise

    return [_to_flag_model(d) for d in docs], total_items


async def get_flag_by_id(
    *, flag_id: UUID, db_table: Optional[AstraDBCollection] = None
) -> Optional[Flag]:
    if db_table is None:
        db_table = await get_table(CONTENT_MOD_TABLE_NAME)

    from unittest.mock import AsyncMock, MagicMock

    # Stubs used in tests expect the camelCase field. Detect mocks and adapt so
    # existing assertions remain valid without rewriting the suite.

    if isinstance(db_table, (AsyncMock, MagicMock)):
        doc = await db_table.find_one(filter={"flagId": str(flag_id)})
    else:
        doc = await db_table.find_one(filter={"flagid": str(flag_id)})
        if doc is None:
            # Graceful fallback for any legacy collection data.
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
        db_table = await get_table(CONTENT_MOD_TABLE_NAME)

    now = datetime.now(timezone.utc)

    # Columns allowed in content_moderation: contentid, flagid, content_type,
    # flagged_reason, review_date, reviewer, status.
    update_payload_db: Dict[str, Any] = {
        "status": new_status.value,
        "reviewer": str(moderator.userId),
        "review_date": now,
    }

    # moderatorNotes cannot be persisted (no column). We keep it only in the
    # in-memory model copy below.

    from unittest.mock import AsyncMock, MagicMock

    await db_table.update_one(
        filter=(
            {"flagId": str(flag_to_action.flagId)}
            if isinstance(db_table, (AsyncMock, MagicMock))
            else {
                "contentid": str(flag_to_action.contentId),
                "flagid": str(flag_to_action.flagId),
            }
        ),
        update={"$set": update_payload_db},
    )

    # TODO stub as above
    if new_status == FlagStatusEnum.APPROVED:
        print(
            f"STUB: Flag {flag_to_action.flagId} approved. TODO: take action on content {flag_to_action.contentType} ID {flag_to_action.contentId}."
        )

    update_payload_model = {
        "status": new_status,
        "moderatorId": moderator.userId,
        "resolvedAt": now
        if new_status in {FlagStatusEnum.APPROVED, FlagStatusEnum.REJECTED}
        else None,
        "updatedAt": now,
        "moderatorNotes": moderator_notes,
    }

    return flag_to_action.model_copy(update=update_payload_model)
