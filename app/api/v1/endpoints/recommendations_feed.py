from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.video import VideoSummary
from app.models.common import PaginatedResponse, Pagination
from app.api.v1.dependencies import (
    PaginationParams,
    get_current_viewer,
)
from app.models.user import User
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "/foryou",
    response_model=PaginatedResponse[VideoSummary],
    summary="Personalized 'For You' video recommendations",
)
async def get_for_you_feed(
    current_user: Annotated[User, Depends(get_current_viewer)],
    pagination: PaginationParams = Depends(),
):
    videos, total_items = await recommendation_service.get_personalized_for_you_videos(
        current_user=current_user,
        page=pagination.page,
        page_size=pagination.pageSize,
    )

    total_pages = (total_items + pagination.pageSize - 1) // pagination.pageSize
    return PaginatedResponse[VideoSummary](  # type: ignore[valid-type]
        data=videos,
        pagination=Pagination(
            currentPage=pagination.page,
            pageSize=pagination.pageSize,
            totalItems=total_items,
            totalPages=total_pages,
        ),
    )
