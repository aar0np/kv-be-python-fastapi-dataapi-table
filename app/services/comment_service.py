"""Service layer for managing video comments."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from uuid import uuid4, UUID

from fastapi import HTTPException, status

from app.db.astra_client import get_table, AstraDBCollection
from app.models.comment import CommentCreateRequest, Comment, CommentID
from app.models.user import User
from app.models.video import VideoID, VideoStatusEnum
from app.services import video_service

COMMENTS_TABLE_NAME = "comments"


async def _determine_sentiment(text: str) -> Optional[str]:
    """Placeholder sentiment analysis; returns pos/neu/neg randomly."""

    return random.choice(["positive", "neutral", "negative", None])


async def add_comment_to_video(
    video_id: VideoID,
    request: CommentCreateRequest,
    current_user: User,
    db_table: Optional[AstraDBCollection] = None,
) -> Comment:
    """Add a new comment to a READY video."""

    target_video = await video_service.get_video_by_id(video_id)
    if target_video is None or target_video.status != VideoStatusEnum.READY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not available for comments",
        )

    if db_table is None:
        db_table = await get_table(COMMENTS_TABLE_NAME)

    now = datetime.now(timezone.utc)
    sentiment = await _determine_sentiment(request.text)

    new_comment = Comment(
        commentId=uuid4(),
        videoId=video_id,
        userId=current_user.userId,
        text=request.text,
        createdAt=now,
        updatedAt=now,
        sentiment=sentiment,
    )

    doc = new_comment.model_dump()
    doc["commentId"] = str(doc["commentId"])
    doc["videoId"] = str(doc["videoId"])
    doc["userId"] = str(doc["userId"])

    await db_table.insert_one(document=doc)
    return new_comment


# ---------------------------------------------------------------------------
# Listing helpers
# ---------------------------------------------------------------------------


def _doc_to_comment(doc: Dict[str, Any]) -> Comment:
    """Convert DB dict to Comment model, handling UUIDs."""

    return Comment(
        commentId=UUID(doc["commentId"]),
        videoId=UUID(doc["videoId"]),
        userId=UUID(doc["userId"]),
        text=doc["text"],
        createdAt=doc["createdAt"],
        updatedAt=doc["updatedAt"],
        sentiment=doc.get("sentiment"),
    )


async def list_comments_for_video(
    video_id: VideoID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[Comment], int]:
    if db_table is None:
        db_table = await get_table(COMMENTS_TABLE_NAME)

    query_filter = {"videoId": str(video_id)}
    skip = (page - 1) * page_size
    cursor = db_table.find(
        filter=query_filter, skip=skip, limit=page_size, sort={"createdAt": -1}
    )
    docs = await cursor.to_list(length=page_size) if hasattr(cursor, "to_list") else cursor
    total = await db_table.count_documents(filter=query_filter)
    return [_doc_to_comment(d) for d in docs], total


async def list_comments_by_user(
    user_id: UUID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[Comment], int]:
    if db_table is None:
        db_table = await get_table(COMMENTS_TABLE_NAME)

    query_filter = {"userId": str(user_id)}
    skip = (page - 1) * page_size
    cursor = db_table.find(filter=query_filter, skip=skip, limit=page_size, sort={"createdAt": -1})
    docs = await cursor.to_list(length=page_size) if hasattr(cursor, "to_list") else cursor
    total = await db_table.count_documents(filter=query_filter)
    return [_doc_to_comment(d) for d in docs], total


async def get_comment_by_id(
    comment_id: CommentID,
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[Comment]:
    """Fetch a single comment by its identifier, returning `None` if not found."""

    if db_table is None:
        db_table = await get_table(COMMENTS_TABLE_NAME)

    doc = await db_table.find_one(filter={"commentId": str(comment_id)})
    if doc is None:
        return None

    return _doc_to_comment(doc) 