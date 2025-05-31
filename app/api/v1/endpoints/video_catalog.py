"""API endpoints for the Video Catalog feature set (phase 1 – submission).
"""

from __future__ import annotations

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException, Response

from app.models.video import (
    VideoSubmitRequest,
    VideoDetailResponse,
    VideoStatusResponse,
    VideoID,
    VideoStatusEnum,
    VideoUpdateRequest,
    VideoSummary,
    VideoRatingRequest,
    VideoRatingSummary,
)
from app.models.user import User
from app.api.v1.dependencies import (
    get_current_creator,
    get_current_user_from_token,
    get_video_for_owner_or_moderator_access,
    get_current_viewer,
)
from app.services import video_service
from app.models.common import PaginatedResponse, Pagination
from app.api.v1.dependencies import PaginationParams

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post(
    "",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit YouTube URL (async processing)",
)
async def submit_video(
    request: VideoSubmitRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_creator)],
):
    """Submit a new YouTube video for asynchronous processing.

    Only users with the *creator* or *moderator* role are authorized.
    """

    new_video = await video_service.submit_new_video(
        request=request, current_user=current_user
    )
    background_tasks.add_task(
        video_service.process_video_submission,
        new_video.videoId,
        new_video.youtubeVideoId,
    )
    return new_video


@router.get(
    "/id/{video_id_path:uuid}/status",
    response_model=VideoStatusResponse,
    summary="Processing status",
)
async def get_video_status(
    video_id_path: VideoID,
    current_user: Annotated[User, Depends(get_current_user_from_token)],
):
    """Return processing status for the given video.

    Accessible to the video owner (creator) or any moderator.
    """

    video = await video_service.get_video_by_id(video_id_path)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    is_owner = video.userId == current_user.userId
    is_moderator = "moderator" in current_user.roles
    is_creator_self = "creator" in current_user.roles and is_owner

    if not (is_creator_self or is_moderator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have permission to view status of this video")

    return VideoStatusResponse(videoId=video.videoId, status=video.status)


@router.get(
    "/id/{video_id_path:uuid}",
    response_model=VideoDetailResponse,
    summary="Video details",
)
async def get_video_details(video_id_path: VideoID):
    """Public endpoint returning full video metadata."""

    video = await video_service.get_video_by_id(video_id_path)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    # In future we might restrict non-READY visibility; for now always return
    return video


# ---------------------------------------------------------------------------
# Update endpoint
# ---------------------------------------------------------------------------


@router.put(
    "/id/{video_id_path:uuid}",
    response_model=VideoDetailResponse,
    summary="Update video details",
)
async def update_video(
    video_id_path: VideoID,
    update_request_data: VideoUpdateRequest,
    video_to_update: Annotated[VideoDetailResponse, Depends(get_video_for_owner_or_moderator_access)],
):
    """Allow owner or moderator to update title/desc/tags."""

    updated_video = await video_service.update_video_details(
        video_to_update=video_to_update, update_request=update_request_data
    )
    return updated_video


# ---------------------------------------------------------------------------
# View count and listing endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/id/{video_id_path:uuid}/view",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record playback view",
)
async def record_view(video_id_path: VideoID):
    video = await video_service.get_video_by_id(video_id_path)
    if video is None or video.status != VideoStatusEnum.READY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found or not available")

    await video_service.record_video_view(video_id_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _build_paginated_response(
    data: List["VideoSummary"],
    total_items: int,
    pagination: PaginationParams,
):
    total_pages = (total_items + pagination.pageSize - 1) // pagination.pageSize
    payload = PaginatedResponse(
        data=data,
        pagination=Pagination(
            currentPage=pagination.page,
            pageSize=pagination.pageSize,
            totalItems=total_items,
            totalPages=total_pages,
        ),
    )
    return payload


@router.get(
    "/latest",
    response_model=PaginatedResponse,
    summary="Latest videos",
)
async def get_latest_videos(
    pagination: PaginationParams = Depends(),
):
    data, total = await video_service.list_latest_videos(pagination.page, pagination.pageSize)
    return _build_paginated_response(data, total, pagination)


@router.get(
    "/by-tag/{tag_name}",
    response_model=PaginatedResponse,
    summary="Videos by tag",
)
async def get_videos_by_tag(
    tag_name: str,
    pagination: PaginationParams = Depends(),
):
    data, total = await video_service.list_videos_by_tag(tag_name, pagination.page, pagination.pageSize)
    return _build_paginated_response(data, total, pagination)


@router.get(
    "/by-uploader/{uploader_id_path}",
    response_model=PaginatedResponse,
    summary="Videos by uploader",
)
async def get_videos_by_uploader(
    uploader_id_path: UUID,
    pagination: PaginationParams = Depends(),
):
    data, total = await video_service.list_videos_by_user(uploader_id_path, pagination.page, pagination.pageSize)
    return _build_paginated_response(data, total, pagination)


# ---------------------------------------------------------------------------
# Ratings endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/id/{video_id_path:uuid}/rating",
    response_model=VideoRatingSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Submit rating (1-5)",
)
async def submit_rating(
    video_id_path: VideoID,
    rating_req: VideoRatingRequest,
    current_user: Annotated[User, Depends(get_current_viewer)],
):
    rating_summary = await video_service.record_rating(
        video_id_path, current_user, rating_req
    )
    return rating_summary


@router.get(
    "/id/{video_id_path:uuid}/rating",
    response_model=VideoRatingSummary,
    summary="Get rating summary",
)
async def get_rating_summary_endpoint(video_id_path: VideoID):
    summary = await video_service.get_rating_summary(video_id_path)
    return summary 