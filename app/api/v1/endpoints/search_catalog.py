from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Query

from app.models.video import VideoSummary, TagSuggestion
from app.models.common import PaginatedResponse, Pagination
from app.api.v1.dependencies import PaginationParams
from app.services import video_service

router = APIRouter(prefix="/search", tags=["Search"])


def _build_paginated_response(data: List[VideoSummary], total: int, pagination: PaginationParams):
    total_pages = (total + pagination.pageSize - 1) // pagination.pageSize
    return PaginatedResponse(
        data=data,
        pagination=Pagination(
            currentPage=pagination.page,
            pageSize=pagination.pageSize,
            totalItems=total,
            totalPages=total_pages,
        ),
    )


@router.get(
    "/videos",
    response_model=PaginatedResponse,
    summary="Keyword video search",
)
async def search_videos(
    query: Annotated[str, Query(min_length=1, description="Search query term")],
    pagination: PaginationParams = Depends(),
):
    summaries, total = await video_service.search_videos_by_keyword(
        query=query, page=pagination.page, page_size=pagination.pageSize
    )
    return _build_paginated_response(summaries, total, pagination)


@router.get(
    "/tags/suggest",
    response_model=List[TagSuggestion],
    summary="Autocomplete tags",
)
async def suggest_video_tags(
    query: Annotated[str, Query(min_length=1, description="Partial tag to search for")],
    limit: Annotated[int, Query(ge=1, le=25, description="Maximum number of suggestions")] = 10,
):
    return await video_service.suggest_tags(query=query, limit=limit) 