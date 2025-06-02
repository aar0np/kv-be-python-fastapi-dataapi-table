from __future__ import annotations

import random
from typing import List

from app.models.video import VideoID
from app.models.recommendation import RecommendationItem
from app.services import video_service


async def get_related_videos(video_id: VideoID, limit: int = 10) -> List[RecommendationItem]:
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

    latest_summaries, _total = await video_service.list_latest_videos(page=1, page_size=limit + 5)

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