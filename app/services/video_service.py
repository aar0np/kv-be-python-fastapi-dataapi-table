"""Business logic for the Video Catalog feature set.

At this stage we only implement the operations needed for submitting a new
video and a helper for parsing YouTube URLs. Additional functions (retrieval,
updates, listing, etc.) will be added incrementally as the epic progresses.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from app.db.astra_client import get_table, AstraDBCollection
from app.models.video import (
    VideoSubmitRequest,
    Video,
    VideoStatusEnum,
    VideoID,
    VideoUpdateRequest,
    VideoSummary,
    VideoRatingRequest,
    VideoRatingSummary,
    TagSuggestion,
)
from app.models.user import User

# ---------------------------------------------------------------------------
# Constants & Regex Patterns
# ---------------------------------------------------------------------------

VIDEOS_TABLE_NAME: str = "videos"
VIDEO_RATINGS_TABLE_NAME: str = "video_ratings"

# A collection of regex patterns that match the majority of YouTube URL formats
# and capture the video ID in a named group called "id".
_YOUTUBE_PATTERNS: List[re.Pattern[str]] = [
    # https://youtu.be/<id>
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/(?P<id>[A-Za-z0-9_-]{11})"),
    # https://www.youtube.com/watch?v=<id>
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=(?P<id>[A-Za-z0-9_-]{11})"
    ),
    # https://www.youtube.com/embed/<id>
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/(?P<id>[A-Za-z0-9_-]{11})"),
    # https://www.youtube.com/v/<id>
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/(?P<id>[A-Za-z0-9_-]{11})"),
    # https://www.youtube.com/shorts/<id>
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/(?P<id>[A-Za-z0-9_-]{11})"
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_youtube_video_id(youtube_url: str) -> Optional[str]:
    """Extract the 11-character YouTube video ID from a variety of URL formats.

    Parameters
    ----------
    youtube_url:
        The URL provided by the user.

    Returns
    -------
    str | None
        The extracted video ID, or ``None`` if no pattern matched.
    """

    for pattern in _YOUTUBE_PATTERNS:
        match = pattern.match(youtube_url)
        if match:
            return match.group("id")
    return None


def _video_to_document(video: Video) -> Dict[str, Any]:
    """Convert a ``Video`` model to the dict format expected by AstraDB JSON."""

    doc = video.model_dump(mode="python")  # returns plain python types

    # Convert UUIDs to strings because AstraDB JSON stores them as varchar
    doc["videoId"] = str(video.videoId)
    doc["userId"] = str(video.userId)
    return doc


def _document_to_video(doc: Dict[str, Any]) -> Video:
    """Convert a DB document back into a ``Video`` Pydantic model."""

    # Ensure UUID fields are converted back to UUID objects
    if "videoId" in doc:
        doc["videoId"] = UUID(doc["videoId"])
    if "userId" in doc:
        doc["userId"] = UUID(doc["userId"])
    return Video(**doc)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Service Operations
# ---------------------------------------------------------------------------

async def submit_new_video(
    request: VideoSubmitRequest,
    current_user: User,
    db_table: Optional[AstraDBCollection] = None,
) -> Video:
    """Persist a new *pending* video record and return the canonical model.

    The heavy-weight processing (fetching YouTube metadata, generating
    thumbnails/embeddings, etc.) will happen later in a background task.
    """

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    youtube_id = extract_youtube_video_id(str(request.youtubeUrl))
    if youtube_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL or unable to extract video ID",
        )

    now = datetime.now(timezone.utc)
    new_video = Video(
        videoId=uuid4(),
        userId=current_user.userId,
        youtubeVideoId=youtube_id,
        submittedAt=now,
        updatedAt=now,
        status=VideoStatusEnum.PENDING,
        title="Video Title Pending Processing",
        description=None,
        tags=[],
        thumbnailUrl=None,
        viewCount=0,
        averageRating=None,
    )

    await db_table.insert_one(document=_video_to_document(new_video))
    return new_video


async def process_video_submission(video_id: VideoID, youtube_video_id: str) -> None:  # noqa: D401,E501
    """Background task stub that will eventually process submitted videos.

    For now we simply log the invocation so we can confirm the task was queued.
    """

    print(
        f"BACKGROUND TASK: Processing video {video_id} for YouTube ID {youtube_video_id}. "
        "TODO: Implement actual processing."
    )


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


async def get_video_by_id(
    video_id: VideoID, db_table: Optional[AstraDBCollection] = None
) -> Optional[Video]:
    """Fetch a single video by its ID.

    Parameters
    ----------
    video_id:
        The UUID of the video to load.
    db_table:
        Optional pre-fetched AstraDB collection – primarily used for unit tests.

    Returns
    -------
    Video | None
        The corresponding ``Video`` model or ``None`` if not found.
    """

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    doc = await db_table.find_one(filter={"videoId": str(video_id)})
    if doc is None:
        return None
    return _document_to_video(doc)


async def update_video_details(
    video_to_update: Video,
    update_request: VideoUpdateRequest,
    db_table: Optional[AstraDBCollection] = None,
) -> Video:
    """Update mutable fields of a video (title, description, tags)."""

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    update_fields = update_request.model_dump(exclude_unset=True)
    if not update_fields:
        # Nothing to update – return original video
        return video_to_update

    update_fields["updatedAt"] = datetime.now(timezone.utc)

    await db_table.update_one(
        filter={"videoId": str(video_to_update.videoId)},
        update={"$set": update_fields},
    )

    updated_data = {**video_to_update.model_dump(), **update_fields}
    # Convert string UUIDs back if replaced
    updated_data["videoId"] = video_to_update.videoId
    updated_data["userId"] = video_to_update.userId
    return Video(**updated_data)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Views & Listing
# ---------------------------------------------------------------------------

async def record_video_view(
    video_id: VideoID, db_table: Optional[AstraDBCollection] = None
) -> bool:
    """Increment the view count for a video in an atomic-ish way."""

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    doc = await db_table.find_one(filter={"videoId": str(video_id)})
    if doc is None:
        return False

    current_views = int(doc.get("viewCount", 0))
    await db_table.update_one(
        filter={"videoId": str(video_id)},
        update={"$set": {"viewCount": current_views + 1}},
    )
    return True


async def list_videos_with_query(
    query_filter: Dict[str, Any],
    page: int,
    page_size: int,
    sort_options: Optional[Dict[str, Any]] = None,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    """Generic helper to run a paginated query and map to summaries."""

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    if sort_options is None:
        sort_options = {"submittedAt": -1}

    skip = (page - 1) * page_size

    cursor = db_table.find(
        filter=query_filter, skip=skip, limit=page_size, sort=sort_options
    )

    docs: List[Dict[str, Any]] = []
    if hasattr(cursor, "to_list"):
        docs = await cursor.to_list(length=page_size)
    else:  # Stub collection path
        docs = cursor  # type: ignore[assignment]

    total_items = await db_table.count_documents(filter=query_filter)

    summaries: List[VideoSummary] = []
    for d in docs:
        # Convert fields
        d_video_id = UUID(d["videoId"])
        d_user_id = UUID(d["userId"])
        summaries.append(
            VideoSummary(
                videoId=d_video_id,
                title=d["title"],
                thumbnailUrl=d.get("thumbnailUrl"),
                userId=d_user_id,
                submittedAt=d["submittedAt"],
                viewCount=d.get("viewCount", 0),
                averageRating=d.get("averageRating"),
            )
        )

    return summaries, total_items


async def list_latest_videos(
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    return await list_videos_with_query(
        {"status": VideoStatusEnum.READY}, page, page_size, db_table=db_table
    )


async def list_videos_by_tag(
    tag: str,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    query_filter = {
        "status": VideoStatusEnum.READY,
        "tags": {"$in": [tag]},
    }
    return await list_videos_with_query(query_filter, page, page_size, db_table=db_table)


async def list_videos_by_user(
    user_id: UUID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    query_filter = {
        "status": VideoStatusEnum.READY,
        "userId": str(user_id),
    }
    return await list_videos_with_query(query_filter, page, page_size, db_table=db_table)


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


async def record_rating(
    video_id: VideoID,
    current_user: User,
    rating_req: VideoRatingRequest,
    ratings_table: Optional[AstraDBCollection] = None,
    videos_table: Optional[AstraDBCollection] = None,
) -> VideoRatingSummary:
    """Record or update the caller's rating, return updated summary."""

    if ratings_table is None:
        ratings_table = await get_table(VIDEO_RATINGS_TABLE_NAME)
    if videos_table is None:
        videos_table = await get_table(VIDEOS_TABLE_NAME)

    # Upsert user rating doc
    await ratings_table.update_one(
        filter={"videoId": str(video_id), "userId": str(current_user.userId)},
        update={"$set": {"rating": rating_req.rating}},
        upsert=True,
    )

    # Recalculate average and count (simple implementation)
    all_ratings_cursor = ratings_table.find(filter={"videoId": str(video_id)})
    ratings_list: List[Dict[str, Any]] = []
    if hasattr(all_ratings_cursor, "to_list"):
        ratings_list = await all_ratings_cursor.to_list(length=None)
    else:
        ratings_list = all_ratings_cursor  # type: ignore[assignment]

    count = len(ratings_list)
    avg = (
        sum(int(doc["rating"]) for doc in ratings_list) / count
        if count > 0
        else 0.0
    )

    # Update video doc
    await videos_table.update_one(
        filter={"videoId": str(video_id)},
        update={"$set": {"averageRating": avg}},
    )

    return VideoRatingSummary(videoId=video_id, averageRating=avg, ratingCount=count)


async def get_rating_summary(
    video_id: VideoID, ratings_table: Optional[AstraDBCollection] = None
) -> VideoRatingSummary:
    if ratings_table is None:
        ratings_table = await get_table(VIDEO_RATINGS_TABLE_NAME)

    cursor = ratings_table.find(filter={"videoId": str(video_id)})
    ratings_list: List[Dict[str, Any]] = []
    if hasattr(cursor, "to_list"):
        ratings_list = await cursor.to_list(length=None)
    else:
        ratings_list = cursor  # type: ignore[assignment]

    count = len(ratings_list)
    avg = (
        sum(int(doc["rating"]) for doc in ratings_list) / count
        if count > 0
        else 0.0
    )

    return VideoRatingSummary(videoId=video_id, averageRating=avg, ratingCount=count)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def search_videos_by_keyword(
    query: str,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    """Basic case-insensitive substring search across title, description, tags."""

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    escaped = re.escape(query)
    search_filter: Dict[str, Any] = {
        "status": VideoStatusEnum.READY.value,
        "$or": [
            {"title": {"$regex": escaped, "$options": "i"}},
            {"description": {"$regex": escaped, "$options": "i"}},
            {"tags": {"$regex": escaped, "$options": "i"}},
        ],
    }

    return await list_videos_with_query(
        query_filter=search_filter,
        page=page,
        page_size=page_size,
        sort_options={"submittedAt": -1},
        db_table=db_table,
    )


# ---------------------------------------------------------------------------
# Tag suggestions
# ---------------------------------------------------------------------------


async def suggest_tags(
    query: str,
    limit: int = 10,
    db_table: Optional[AstraDBCollection] = None,
) -> List[TagSuggestion]:
    """Return tag suggestions containing the query substring (case-insensitive)."""

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    # Fetch tags field from a subset of recent videos
    cursor = db_table.find(
        filter={
            "status": VideoStatusEnum.READY.value,
            "tags": {"$exists": True},
        },
        projection={"tags": 1},
        limit=2000,
        sort={"submittedAt": -1},
    )

    import asyncio
    if asyncio.iscoroutine(cursor):
        cursor = await cursor
    if hasattr(cursor, "to_list"):
        raw_docs = await cursor.to_list(length=None)
    else:
        raw_docs = cursor  # type: ignore[assignment]

    tag_set: set[str] = set()
    for doc in raw_docs:
        tags_field = doc.get("tags")
        if isinstance(tags_field, list):
            for t in tags_field:
                if isinstance(t, str):
                    tag_set.add(t)

    matching = [t for t in sorted(tag_set) if query.lower() in t.lower()]
    return [TagSuggestion(tag=t) for t in matching[:limit]]


async def restore_video(video_id: VideoID) -> bool:
    """Stub to mark video for restoration (no-op)."""

    video = await get_video_by_id(video_id)
    if video is None:
        print(f"STUB: Video {video_id} not found for restore.")
        return False
    print(f"STUB: Restoring video {video_id}. Currently deleted: {getattr(video, 'is_deleted', False)}")
    return True 