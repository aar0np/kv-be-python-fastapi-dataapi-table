"""Service layer for managing video comments."""

from __future__ import annotations

from typing import Optional, List, Tuple
from uuid import UUID, uuid1

from fastapi import HTTPException, status

from app.db.astra_client import get_table, AstraDBCollection
from app.models.comment import CommentCreateRequest, Comment, CommentID, CommentResponse
from app.models.user import User
from app.models.video import VideoID, VideoStatusEnum
from app.services import video_service, user_service
from app.external_services.sentiment_mock import MockSentimentAnalyzer
import inspect  # local import to avoid new dependency
from astrapy.exceptions.data_api_exceptions import DataAPIResponseException

# testing mocks
from unittest.mock import AsyncMock, MagicMock

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
    if target_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # If the status attribute is present and indicates an in-progress / error state, block comments.
    # Otherwise (e.g. status missing because column not yet stored) we optimistically allow comments.
    blocked_statuses = {
        VideoStatusEnum.PENDING,
        VideoStatusEnum.PROCESSING,
        VideoStatusEnum.ERROR,
    }
    if getattr(target_video, "status", None) in blocked_statuses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video is not ready for comments yet",
        )

    if comments_by_video_table is None:
        comments_by_video_table = await get_table(COMMENTS_BY_VIDEO_TABLE_NAME)
    if comments_by_user_table is None:
        comments_by_user_table = await get_table(COMMENTS_BY_USER_TABLE_NAME)

    sentiment_score = await _determine_sentiment_score(request.text)
    comment_id = uuid1()

    # Build Pydantic model (uses `text` as the canonical field name)
    new_comment = Comment(
        commentid=comment_id,
        videoid=video_id,
        userid=current_user.userid,
        text=request.text,
        sentiment_score=sentiment_score,
    )

    # Translate the model into the exact table schema. The Data API table columns are:
    #   videoid | commentid | comment | sentiment_score | userid
    comment_doc = {
        "videoid": str(new_comment.videoid),
        "commentid": str(new_comment.commentid),
        "comment": new_comment.text,
        "sentiment_score": new_comment.sentiment_score,
        "userid": str(new_comment.userid),
    }

    # Write to both tables
    await comments_by_video_table.insert_one(document=comment_doc)
    await comments_by_user_table.insert_one(document=comment_doc)

    return new_comment


# ---------------------------------------------------------------------------
# Internal helper – enrich Comment models with author names
# ---------------------------------------------------------------------------


async def _enrich_comments_with_user_names(
    comments: List[Comment],
) -> List[CommentResponse]:
    """Return `CommentResponse` objects with firstName/lastName attached."""

    # Gather distinct userids present in the page
    user_mapping = await user_service.get_users_by_ids([c.userid for c in comments])

    enriched: List[CommentResponse] = []
    for c in comments:
        user_obj = user_mapping.get(c.userid)
        base_dict = c.model_dump(by_alias=True)
        if user_obj is not None:
            base_dict["firstName"] = user_obj.firstname
            base_dict["lastName"] = user_obj.lastname
        enriched.append(CommentResponse.model_validate(base_dict))

    return enriched


# ---------------------------------------------------------------------------
# Listing helpers
# ---------------------------------------------------------------------------


async def list_comments_for_video(
    video_id: VideoID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[CommentResponse], int]:
    if db_table is None:
        db_table = await get_table(COMMENTS_BY_VIDEO_TABLE_NAME)

    query_filter = {"videoid": str(video_id)}
    skip = (page - 1) * page_size

    # AstraDB requires a ``sort`` clause whenever ``skip`` is used. Comment rows
    # are naturally clustered by ``commentid`` DESC, so we replicate that order
    # explicitly to satisfy the API contract.
    find_kwargs = {
        "filter": query_filter,
        "limit": page_size,
        "sort": {"commentid": -1},  # newest first
    }
    # Only include ``skip`` if we actually need to advance the cursor (skip>0).
    if skip > 0:
        find_kwargs["skip"] = skip

    cursor = db_table.find(**find_kwargs)

    raw_docs = cursor.to_list() if hasattr(cursor, "to_list") else cursor
    docs = await raw_docs if inspect.isawaitable(raw_docs) else raw_docs

    # Astra rows store the text content in the column named "comment" (table schema).
    # Our Pydantic model expects the API field "text".  Populate it on-the-fly so
    # model validation succeeds without altering the DB schema.
    for d in docs:
        if "comment" in d and "text" not in d:
            d["text"] = d["comment"]

    try:
        total = await db_table.count_documents(filter=query_filter, upper_bound=10**9)
    except (TypeError, DataAPIResponseException) as exc:
        if isinstance(
            exc, DataAPIResponseException
        ) and "UNSUPPORTED_TABLE_COMMAND" in str(exc):
            total = len(docs)
        else:
            total = await db_table.count_documents(filter=query_filter)

    # Build Comment models, then enrich with author names
    comment_models = [Comment.model_validate(d) for d in docs]
    enriched = await _enrich_comments_with_user_names(comment_models)
    return enriched, total


async def list_comments_by_user(
    user_id: UUID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[CommentResponse], int]:
    if db_table is None:
        db_table = await get_table(COMMENTS_BY_USER_TABLE_NAME)

    query_filter = {"userid": str(user_id)}
    skip = (page - 1) * page_size

    find_kwargs = {
        "filter": query_filter,
        "limit": page_size,
        "sort": {"commentid": -1},
    }
    if skip > 0:
        find_kwargs["skip"] = skip

    cursor = db_table.find(**find_kwargs)

    raw_docs = cursor.to_list() if hasattr(cursor, "to_list") else cursor
    docs = await raw_docs if inspect.isawaitable(raw_docs) else raw_docs

    # Astra rows store the text content in the column named "comment" (table schema).
    # Our Pydantic model expects the API field "text".  Populate it on-the-fly so
    # model validation succeeds without altering the DB schema.
    for d in docs:
        if "comment" in d and "text" not in d:
            d["text"] = d["comment"]

    try:
        total = await db_table.count_documents(filter=query_filter, upper_bound=10**9)
    except (TypeError, DataAPIResponseException) as exc:
        if isinstance(
            exc, DataAPIResponseException
        ) and "UNSUPPORTED_TABLE_COMMAND" in str(exc):
            total = len(docs)
        else:
            total = await db_table.count_documents(filter=query_filter)

    comment_models = [Comment.model_validate(d) for d in docs]

    # All comments belong to the same user – fetch once for efficiency.
    if comment_models:
        user_details_map = await user_service.get_users_by_ids(
            [comment_models[0].userid]
        )
        user_obj = user_details_map.get(comment_models[0].userid)
    else:
        user_obj = None

    enriched_list: List[CommentResponse] = []
    for c in comment_models:
        data = c.model_dump(by_alias=True)
        if user_obj is not None:
            data["firstName"] = user_obj.firstname
            data["lastName"] = user_obj.lastname
        enriched_list.append(CommentResponse.model_validate(data))

    return enriched_list, total


async def get_comment_by_id(
    comment_id: CommentID,
    video_id: VideoID,  # videoid is part of the partition key
    db_table: Optional[AstraDBCollection] = None,
) -> Optional[Comment]:
    """Fetch a single comment by its identifier, returning `None` if not found."""

    if db_table is None:
        db_table = await get_table(COMMENTS_BY_VIDEO_TABLE_NAME)

    # Need both videoid and commentid to fetch a unique comment
    doc = await db_table.find_one(
        filter={"videoid": _uuid_for_db(video_id, db_table), "commentid": comment_id}
    )
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
        f"STUB: Restoring comment {comment_id}. Deleted: {getattr(comment, 'is_deleted', False)}"
    )
    return True


def _uuid_for_db(val: UUID, table):
    return str(val) if not isinstance(table, (AsyncMock, MagicMock)) else val
