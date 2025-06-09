from __future__ import annotations

import random
from typing import List, Tuple

from app.models.video import VideoID, VideoSummary
from app.models.recommendation import (
    RecommendationItem,
    EmbeddingIngestRequest,
    EmbeddingIngestResponse,
)
from app.services import video_service
from app.models.user import User


async def get_related_videos(
    video_id: VideoID, limit: int = 10
) -> List[RecommendationItem]:
    """Return a stubbed *related videos* list.

    In a future iteration this will call into a real recommendation engine that
    analyses the content of the referenced video to find similar items. For the
    moment we simply return the latest videos (excluding the reference video)
    and assign each a random relevance score.
    """

    # Ensure the referenced video exists – if it does not, we treat the request
    # as valid but return an empty list. The caller is free to 404 at the API
    # layer if it wishes to enforce existence – keeping this generic allows the
    # service to be reused from different contexts.
    target_video = await video_service.get_video_by_id(video_id)
    if target_video is None:
        return []

    latest_summaries, _total = await video_service.list_latest_videos(
        page=1, page_size=limit + 5
    )

    related_items: List[RecommendationItem] = []

    for summary in latest_summaries:
        if summary.videoId == video_id:
            # Skip the source video itself
            continue
        if len(related_items) >= limit:
            break
        related_items.append(
            RecommendationItem(
                videoId=summary.videoId,
                title=summary.title,
                thumbnailUrl=summary.thumbnailUrl,
                score=round(random.uniform(0.5, 1.0), 2),
            )
        )

    return related_items


async def get_personalized_for_you_videos(
    current_user: User,
    page: int,
    page_size: int,
) -> Tuple[List[VideoSummary], int]:
    """Return a stubbed personalised feed for *current_user*.

    The implementation simply proxies to :pyfunc:`video_service.list_latest_videos` for now, but the
    function signature and logging establish the contract expected by higher layers so that a real
    recommender can be dropped-in later without further API changes.
    """

    # For visibility during development/testing.
    print(
        f"STUB: Generating 'For You' feed for user {current_user.userId} (page={page}, page_size={page_size})"
    )

    videos, total_items = await video_service.list_latest_videos(
        page=page, page_size=page_size
    )
    return videos, total_items


# ---------------------------------------------------------------------------
# Embedding ingestion stub
# ---------------------------------------------------------------------------


async def ingest_video_embedding(
    request: EmbeddingIngestRequest,
) -> EmbeddingIngestResponse:
    """Receive and store (stub) a video's vector embedding.

    A real implementation would persist the vector into a vector database or as part of the
    video document. For now we simply validate that the video exists and return an acknowledgement.
    """

    target_video = await video_service.get_video_by_id(request.videoId)

    if target_video is None:
        # Service chooses to return an error payload; router may convert to HTTPException.
        return EmbeddingIngestResponse(
            videoId=request.videoId,
            status="error",
            message=f"Video {request.videoId} not found.",
        )

    print(
        f"STUB: Received embedding for video {request.videoId}. "
        f"Vector dimension: {len(request.vector)}. First 3 dims: {request.vector[:3]}"
    )

    # Placeholder for updating database / vector store.

    return EmbeddingIngestResponse(
        videoId=request.videoId,
        status="received_stub",
        message="Embedding data received and acknowledged (stub).",
    )
