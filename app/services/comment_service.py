"""Service layer for managing video comments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from uuid import uuid4, UUID, uuid1

from fastapi import HTTPException, status

from app.db.astra_client import get_table, AstraDBCollection
from app.models.comment import CommentCreateRequest, Comment, CommentID
from app.models.user import User
from app.models.video import VideoID, VideoStatusEnum
from app.services import video_service
from app.external_services.sentiment_mock import MockSentimentAnalyzer

COMMENTS_BY_VIDEO_TABLE_NAME = "comments"
COMMENTS_BY_USER_TABLE_NAME = "comments_by_user"


async def _determine_sentiment_score(text: str) -> Optional[float]:
    """Determine sentiment using a mocked analyser for deterministic results."""
    analyzer = MockSentimentAnalyzer()
    # This mock now returns a float score instead of a string
    return await analyzer.analyze_score(text)


async def add_comment_to_video(
    video_id: VideoID,
    request: CommentCreateRequest,
    current_user: User,
    comments_by_video_table: Optional[AstraDBCollection] = None,
    comments_by_user_table: Optional[AstraDBCollection] = None,
) -> Comment:
    """Add a new comment to a READY video, denormalizing for queries."""

    target_video = await video_service.get_video_by_id(video_id)
    if target_video is None or target_video.status != VideoStatusEnum.READY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not available for comments",
        )

    if comments_by_video_table is None:
        comments_by_video_table = await get_table(COMMENTS_BY_VIDEO_TABLE_NAME)
    if comments_by_user_table is None:
        comments_by_user_table = await get_table(COMMENTS_BY_USER_TABLE_NAME)

    sentiment_score = await _determine_sentiment_score(request.text)
    comment_id = uuid1()

    new_comment = Comment(
        commentid=comment_id,
        videoid=video_id,
        userid=current_user.userid,
        comment=request.text,
        sentiment_score=sentiment_score,
        text=request.text,
    )

    comment_doc = new_comment.model_dump(by_alias=False)

    # Write to both tables
    await comments_by_video_table.insert_one(document=comment_doc)
    await comments_by_user_table.insert_one(document=comment_doc)

    return new_comment


# ---------------------------------------------------------------------------
# Listing helpers
# ---------------------------------------------------------------------------


async def list_comments_for_video(
    video_id: VideoID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[Comment], int]:
    if db_table is None:
        db_table = await get_table(COMMENTS_BY_VIDEO_TABLE_NAME)

    # Note: AstraDB/Cassandra pagination is complex. A simple skip is not
    # efficient. True pagination requires tracking paging state tokens.
    # For this project, we'll use the simpler offset-based approach.
    query_filter = {"videoid": video_id}
    skip = (page - 1) * page_size

    # The 'comments' table is ordered by commentid DESC, so no explicit sort is needed.
    import inspect  # local import to avoid new dependency

    cursor = db_table.find(filter=query_filter, skip=skip, limit=page_size)

    raw_docs = (
        cursor.to_list() if hasattr(cursor, "to_list") else cursor
    )
    docs = await raw_docs if inspect.isawaitable(raw_docs) else raw_docs
    try:
        total = await db_table.count_documents(filter=query_filter, upper_bound=10**9)
    except TypeError:
        total = await db_table.count_documents(filter=query_filter)
    return [Comment.model_validate(d) for d in docs], total


async def list_comments_by_user(
    user_id: UUID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[Comment], int]:
    if db_table is None:
        db_table = await get_table(COMMENTS_BY_USER_TABLE_NAME)

    query_filter = {"userid": user_id}
    skip = (page - 1) * page_size

    # The 'comments_by_user' table is ordered by commentid DESC.
    import inspect

    cursor = db_table.find(filter=query_filter, skip=skip, limit=page_size)

    raw_docs = (
        cursor.to_list() if hasattr(cursor, "to_list") else cursor
    )
    docs = await raw_docs if inspect.isawaitable(raw_docs) else raw_docs
    try:
        total = await db_table.count_documents(filter=query_filter, upper_bound=10**9)
    except TypeError:
        total = await db_table.count_documents(filter=query_filter)
    return [Comment.model_validate(d) for d in docs], total


async def get_comment_by_id(
    comment_id: CommentID,
    video_id: VideoID,  # videoid is part of the partition key
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[Comment]:
    """Fetch a single comment by its identifier, returning `None` if not found."""

    if db_table is None:
        db_table = await get_table(COMMENTS_BY_VIDEO_TABLE_NAME)

    # Need both videoid and commentid to fetch a unique comment
    doc = await db_table.find_one(filter={"videoid": video_id, "commentid": comment_id})
    if doc is None:
        return None

    return Comment.model_validate(doc)


async def restore_comment(comment_id: CommentID, video_id: VideoID) -> bool:
    """Stub restore comment."""
    comment = await get_comment_by_id(comment_id, video_id)
    if comment is None:
        print(f"STUB: Comment {comment_id} not found for restore.")
        return False
    print(
        f"STUB: Restoring comment {comment_id}. Deleted: {getattr(comment,'is_deleted',False)}"
    )
    return True
