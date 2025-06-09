from __future__ import annotations

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.models.comment import CommentCreateRequest, CommentResponse, Comment
from app.models.video import VideoID
from app.models.user import User
from app.api.v1.dependencies import (
    get_current_viewer,
    PaginationParams,
    get_current_user_optional,
)
from app.models.common import PaginatedResponse, Pagination
from app.services import comment_service, rating_service
from app.models.rating import (
    RatingCreateOrUpdateRequest,
    RatingResponse,
    AggregateRatingResponse,
)

router = APIRouter(tags=["Comments & Ratings"])


@router.post(
    "/videos/{video_id_path:uuid}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to video",
)
async def post_comment_to_video(
    video_id_path: VideoID,
    comment_data: CommentCreateRequest,
    current_user: Annotated[User, Depends(get_current_viewer)],
):
    """Endpoint for viewers to add a comment to a READY video."""

    new_comment = await comment_service.add_comment_to_video(
        video_id=video_id_path, request=comment_data, current_user=current_user
    )
    return CommentResponse.model_validate(new_comment)


# pagination helper


def _build_paginated(data: List[Comment], total: int, pagination: PaginationParams):
    response_data = [CommentResponse.model_validate(c) for c in data]
    pages = (total + pagination.pageSize - 1) // pagination.pageSize
    return PaginatedResponse(
        data=response_data,
        pagination=Pagination(
            currentPage=pagination.page,
            pageSize=pagination.pageSize,
            totalItems=total,
            totalPages=pages,
        ),
    )


@router.get(
    "/videos/{video_id_path:uuid}/comments",
    response_model=PaginatedResponse,
    summary="List comments for video",
)
async def list_comments_video(
    video_id_path: VideoID,
    pagination: PaginationParams = Depends(),
):
    comments, total = await comment_service.list_comments_for_video(
        video_id=video_id_path, page=pagination.page, page_size=pagination.pageSize
    )
    return _build_paginated(comments, total, pagination)


@router.get(
    "/users/{user_id_path:uuid}/comments",
    response_model=PaginatedResponse,
    summary="List comments by user",
)
async def list_comments_user(
    user_id_path: UUID,
    pagination: PaginationParams = Depends(),
):
    comments, total = await comment_service.list_comments_by_user(
        user_id=user_id_path, page=pagination.page, page_size=pagination.pageSize
    )
    return _build_paginated(comments, total, pagination)


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


@router.post(
    "/videos/{video_id_path:uuid}/ratings",
    response_model=RatingResponse,
    summary="Rate a video (create or update)",
)
async def post_rating_video(
    video_id_path: VideoID,
    rating_data: RatingCreateOrUpdateRequest,
    current_user: Annotated[User, Depends(get_current_viewer)],
):
    """Upsert a rating (1-5) for the specified video by the current viewer."""

    rating_obj = await rating_service.rate_video(
        video_id=video_id_path, request=rating_data, current_user=current_user
    )
    return rating_obj


# ---------------------------------------------------------------------------
# Ratings summary
# ---------------------------------------------------------------------------


@router.get(
    "/videos/{video_id_path:uuid}/ratings",
    response_model=AggregateRatingResponse,
    summary="Get aggregate rating plus current user's rating (optional)",
)
async def get_rating_summary_video(
    video_id_path: VideoID,
    current_user_opt: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    user_id = current_user_opt.userId if current_user_opt else None
    summary = await rating_service.get_video_ratings_summary(
        video_id=video_id_path, current_user_id=user_id
    )
    return summary
