"""Business logic for the Video Catalog feature set.

At this stage we only implement the operations needed for submitting a new
video and a helper for parsing YouTube URLs. Additional functions (retrieval,
updates, listing, etc.) will be added incrementally as the epic progresses.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
import asyncio
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


from app.external_services.youtube_mock import MockYouTubeService

# ---------------------------------------------------------------------------
# Constants & Regex Patterns
# ---------------------------------------------------------------------------

VIDEOS_TABLE_NAME: str = "videos"
LATEST_VIDEOS_TABLE_NAME: str = "latest_videos"
VIDEO_PLAYBACK_STATS_TABLE_NAME: str = "video_playback_stats"
VIDEO_RATINGS_TABLE_NAME: str = "video_ratings_by_user"
VIDEO_RATINGS_SUMMARY_TABLE_NAME: str = "video_ratings"

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
        videoid=uuid4(),
        userid=current_user.userid,
        added_date=now,
        name="Video Title Pending Processing",
        location=str(request.youtubeUrl),
        location_type=0,  # 0 for YouTube
        youtubeVideoId=youtube_id,
        updatedAt=now,
    )

    video_doc = new_video.model_dump(by_alias=False, exclude_none=True)
    await db_table.insert_one(document=video_doc)
    return new_video


async def process_video_submission(video_id: VideoID, youtube_video_id: str) -> None:  # noqa: D401,E501
    """Fetch metadata for the submitted YouTube video and update DB status.

    The implementation deliberately stays *lightweight* – it calls a mocked
    YouTube service, writes interim *PROCESSING* state to the database, waits
    a few seconds to emulate work being done, and finally marks the record
    *READY* or *ERROR* depending on whether details were retrieved.
    """

    mock_yt_service = MockYouTubeService()

    # Retrieve video details (this could raise, but the mock simply returns None)
    video_details = await mock_yt_service.get_video_details(youtube_video_id)

    videos_table = await get_table(VIDEOS_TABLE_NAME)
    now = datetime.now(timezone.utc)

    final_status: str = VideoStatusEnum.ERROR.value  # pessimistic default
    update_payload: Dict[str, Any] = {"updatedAt": now}

    if video_details:
        # Interim update – mark as processing with the metadata we have so far
        update_payload.update(
            {
                "name": video_details.get("title", "Title Not Found"),
                "description": video_details.get("description"),
                "preview_image_location": video_details.get("thumbnail_url"),
                "tags": video_details.get("tags", []),
                "status": VideoStatusEnum.PROCESSING.value,
            }
        )

        print(f"BACKGROUND TASK: Video {video_id} - Simulating processing (5s)...")

        # Write interim processing state
        await videos_table.update_one(
            filter={"videoid": video_id}, update={"$set": dict(update_payload)}
        )

        # Simulate lengthy processing
        await asyncio.sleep(5)

        final_status = VideoStatusEnum.READY.value
    else:
        update_payload["name"] = "Error Processing Video: Details Not Found"

    # Final state update
    final_payload = {**update_payload, "status": final_status}

    await videos_table.update_one(
        filter={"videoid": video_id}, update={"$set": final_payload}
    )

    print(
        f"BACKGROUND TASK COMPLETED: Video {video_id} processed. Final Status: {final_status}"
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

    doc = await db_table.find_one(filter={"videoid": video_id})
    if doc is None:
        return None
    return Video.model_validate(doc)


async def update_video_details(
    video_to_update: Video,
    update_request: VideoUpdateRequest,
    db_table: Optional[AstraDBCollection] = None,
) -> Video:
    """Update mutable fields of a video (title, description, tags)."""

    if db_table is None:
        db_table = await get_table(VIDEOS_TABLE_NAME)

    update_fields = update_request.model_dump(exclude_unset=True, by_alias=False)
    if not update_fields:
        # Nothing to update – return original video
        return video_to_update

    update_fields["updatedAt"] = datetime.now(timezone.utc)

    await db_table.update_one(
        filter={"videoid": video_to_update.videoid},
        update={"$set": update_fields},
    )

    # Re-fetch to get the fully updated model
    updated_video = await get_video_by_id(video_to_update.videoid, db_table)
    if updated_video is None:
        # This should not happen if the video existed before
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found after update.",
        )
    return updated_video


# ---------------------------------------------------------------------------
# Views & Listing
# ---------------------------------------------------------------------------


async def record_video_view(
    video_id: VideoID, db_table: Optional[AstraDBCollection] = None
) -> None:
    """Increment the view count for a video."""

    if db_table is None:
        db_table = await get_table(VIDEO_PLAYBACK_STATS_TABLE_NAME)

    await db_table.update_one(
        filter={"videoid": video_id},
        update={"$inc": {"views": 1}},
        upsert=True,
    )


async def list_videos_with_query(
    query_filter: Dict[str, Any],
    page: int,
    page_size: int,
    sort_options: Optional[Dict[str, Any]] = None,
    db_table: Optional[AstraDBCollection] = None,
    source_table_name: str = VIDEOS_TABLE_NAME,
) -> Tuple[List[VideoSummary], int]:
    """Generic helper to run a paginated query and map to summaries."""

    if db_table is None:
        db_table = await get_table(source_table_name)

    # Default sort for 'videos' table is by submission date
    if sort_options is None:
        if source_table_name == LATEST_VIDEOS_TABLE_NAME:
            sort_options = {
                "added_date": -1
            }  # latest_videos is pre-sorted by day, then added_date
        else:
            sort_options = {"added_date": -1}

    skip = (page - 1) * page_size

    # When querying latest_videos, we need a different approach for pagination and querying
    if source_table_name == LATEST_VIDEOS_TABLE_NAME:
        # For simplicity, this example will just grab the latest day.
        # A more robust solution would handle paging across days.
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        query_filter = {"day": today}

    cursor = db_table.find(
        filter=query_filter, skip=skip, limit=page_size, sort=sort_options
    )

    docs: List[Dict[str, Any]] = []
    if hasattr(cursor, "to_list"):
        docs = await cursor.to_list()
    else:  # Stub collection path
        docs = cursor  # type: ignore[assignment]

    from astrapy.exceptions.data_api_exceptions import DataAPIResponseException
    try:
        total_items = await db_table.count_documents(
            filter=query_filter, upper_bound=10**9
        )
    except (TypeError, DataAPIResponseException):
        # Unsupported on tables or running against stub – use docs length
        total_items = len(docs)

    summaries: List[VideoSummary] = [VideoSummary.model_validate(d) for d in docs]

    return summaries, total_items


async def list_latest_videos(
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    return await list_videos_with_query(
        {},
        page,
        page_size,
        db_table=db_table,
        source_table_name=LATEST_VIDEOS_TABLE_NAME,
    )


async def list_videos_by_tag(
    tag: str,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    query_filter = {
        "tags": {"$in": [tag]},
    }
    return await list_videos_with_query(
        query_filter, page, page_size, db_table=db_table
    )


async def list_videos_by_user(
    user_id: UUID,
    page: int,
    page_size: int,
    db_table: Optional[AstraDBCollection] = None,
) -> Tuple[List[VideoSummary], int]:
    query_filter = {
        "userid": str(user_id),
    }
    return await list_videos_with_query(
        query_filter, page, page_size, db_table=db_table
    )


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


async def record_rating(
    video_id: VideoID,
    current_user: User,
    rating_req: VideoRatingRequest,
    ratings_table: Optional[AstraDBCollection] = None,
    ratings_summary_table: Optional[AstraDBCollection] = None,
) -> None:
    """Record or update the caller's rating and update summary."""

    if ratings_table is None:
        ratings_table = await get_table(VIDEO_RATINGS_TABLE_NAME)
    if ratings_summary_table is None:
        ratings_summary_table = await get_table(VIDEO_RATINGS_SUMMARY_TABLE_NAME)

    # Upsert user rating doc
    await ratings_table.insert_one(
        {
            "videoid": video_id,
            "userid": current_user.userid,
            "rating": rating_req.rating,
            "rating_date": datetime.now(timezone.utc),
        }
    )

    # Update summary table counters
    await ratings_summary_table.update_one(
        filter={"videoid": video_id},
        update={"$inc": {"rating_counter": 1, "rating_total": rating_req.rating}},
        upsert=True,
    )


async def get_rating_summary(
    video_id: VideoID, ratings_summary_table: Optional[AstraDBCollection] = None
) -> VideoRatingSummary:
    if ratings_summary_table is None:
        ratings_summary_table = await get_table(VIDEO_RATINGS_SUMMARY_TABLE_NAME)

    doc = await ratings_summary_table.find_one(filter={"videoid": video_id})

    if not doc:
        return VideoRatingSummary(videoId=video_id, averageRating=0.0, ratingCount=0)

    rating_counter = doc.get("rating_counter", 0)
    rating_total = doc.get("rating_total", 0)
    avg = rating_total / rating_counter if rating_counter > 0 else 0.0

    return VideoRatingSummary(
        videoId=video_id, averageRating=round(avg, 2), ratingCount=rating_counter
    )


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
        "$or": [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"description": {"$regex": escaped, "$options": "i"}},
            {"tags": {"$regex": escaped, "$options": "i"}},
        ],
    }

    return await list_videos_with_query(
        query_filter=search_filter,
        page=page,
        page_size=page_size,
        sort_options={"added_date": -1},
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
            "tags": {"$exists": True},
        },
        projection={"tags": 1},
        limit=2000,
        sort={"added_date": -1},
    )

    if asyncio.iscoroutine(cursor):
        cursor = await cursor
    if hasattr(cursor, "to_list"):
        raw_docs = await cursor.to_list()
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
    print(
        f"STUB: Restoring video {video_id}. Currently deleted: {getattr(video, 'is_deleted', False)}"
    )
    return True
