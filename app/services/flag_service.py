from __future__ import annotations

"""Service layer handling creation and lifecycle of moderation flags."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

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


async def _to_flag_model(doc: dict) -> Flag:
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