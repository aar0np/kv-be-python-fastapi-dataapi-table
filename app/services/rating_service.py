"""Service logic for video ratings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status

from app.db.astra_client import get_table, AstraDBCollection
from app.models.rating import (
    RatingCreateOrUpdateRequest,
    Rating,
    AggregateRatingResponse,
    RatingValue,
)
from app.models.video import VideoID, VideoStatusEnum
from app.models.user import User
from app.services import video_service
from astrapy.exceptions.data_api_exceptions import DataAPIResponseException

RATINGS_TABLE_NAME = video_service.VIDEO_RATINGS_TABLE_NAME  # "video_ratings_by_user"
RATINGS_SUMMARY_TABLE_NAME = video_service.VIDEO_RATINGS_SUMMARY_TABLE_NAME


async def _update_video_aggregate_rating(
    video_id: VideoID,
    ratings_db_table: AstraDBCollection,
    videos_db_table: AstraDBCollection,
) -> None:
    """Recalculate average and total ratings count for the given video."""

    cursor = ratings_db_table.find(
        filter={"videoid": str(video_id)}, projection={"rating": 1}
    )
    docs: List[Dict[str, Any]] = (
        await cursor.to_list() if hasattr(cursor, "to_list") else cursor
    )

    if docs:
        values = [int(d["rating"]) for d in docs if "rating" in d]
        total = len(values)
        average = sum(values) / total if total else None
    else:
        total = 0
        average = None

    try:
        await videos_db_table.update_one(
            filter={"videoid": str(video_id)},
            update={
                "$set": {
                    "averageRating": average,
                    "totalRatingsCount": total,
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
        )
    except DataAPIResponseException as exc:
        # If the videos table schema does not include these columns (common
        # when running against the default KillrVideo schema) Astra will
        # reject the update with UNKNOWN_TABLE_COLUMNS.  That is not fatal –
        # the API can still compute aggregates on-the-fly.
        if "UNKNOWN_TABLE_COLUMNS" not in str(exc):
            raise
        # Otherwise silently ignore so the rating operation succeeds.


async def rate_video(
    video_id: VideoID,
    request: RatingCreateOrUpdateRequest,
    current_user: User,
    db_table: Optional[AstraDBCollection] = None,
) -> Rating:
    target_video = await video_service.get_video_by_id(video_id)
    if target_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Videos persisted through the fallback path often lack a ``status`` column
    # (the table schema has no such column).  In that scenario Pydantic fills
    # the attribute with its default (PENDING). We consider *absence* of the
    # field equivalent to READY so that legacy/legacy-imported videos remain
    # rateable.
    status_in_doc = "status" in getattr(target_video, "model_fields_set", set())
    if target_video.status != VideoStatusEnum.READY and status_in_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not available for rating",
        )

    if db_table is None:
        db_table = await get_table(RATINGS_TABLE_NAME)

    now = datetime.now(timezone.utc)
    rating_filter = {"videoid": str(video_id), "userid": str(current_user.userid)}
    existing_doc = await db_table.find_one(filter=rating_filter)

    if existing_doc:
        await db_table.update_one(
            filter=rating_filter,
            update={"$set": {"rating": request.rating, "rating_date": now}},
        )
        created_at = existing_doc.get("rating_date", now)
        rating_obj = Rating(
            videoId=video_id,
            userId=current_user.userid,
            rating=request.rating,
            createdAt=created_at,
            updatedAt=now,
        )
    else:
        rating_obj = Rating(
            videoId=video_id,
            userId=current_user.userid,
            rating=request.rating,
            createdAt=now,
            updatedAt=now,
        )
        insert_doc = {
            "videoid": str(video_id),
            "userid": str(current_user.userid),
            "rating": request.rating,
            "rating_date": now,
        }
        await db_table.insert_one(document=insert_doc)

    # update aggregate
    await _update_video_aggregate_rating(
        video_id, db_table, await get_table(video_service.VIDEOS_TABLE_NAME)
    )
    return rating_obj


# ---------------------------------------------------------------------------
# Aggregate fetch
# ---------------------------------------------------------------------------


async def get_video_ratings_summary(
    video_id: VideoID,
    current_user_id: UUID | None = None,
    ratings_db_table: Optional[AstraDBCollection] = None,
) -> AggregateRatingResponse:
    """Return aggregated rating info for a video and optionally the caller's rating."""

    # Fetch video to access pre-computed aggregates
    target_video = await video_service.get_video_by_id(video_id)
    if target_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    avg = target_video.averageRating
    total = target_video.totalRatingsCount

    user_rating_value: RatingValue | None = None
    if current_user_id is not None:
        if ratings_db_table is None:
            ratings_db_table = await get_table(RATINGS_TABLE_NAME)

        doc = await ratings_db_table.find_one(
            filter={"videoid": str(video_id), "userid": str(current_user_id)},
            projection={"rating": 1},
        )
        if doc and "rating" in doc:
            user_rating_value = int(doc["rating"])

    return AggregateRatingResponse(
        videoId=video_id,
        averageRating=avg,
        totalRatingsCount=total,
        currentUserRating=user_rating_value,
    )
