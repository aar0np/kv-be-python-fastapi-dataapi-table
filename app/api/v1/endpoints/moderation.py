from __future__ import annotations

"""Endpoints reserved for moderator actions (flag inbox, flag actions, role mgmt stubs)."""

from typing import Annotated, Optional, List
from uuid import UUID
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.dependencies import (
    get_current_moderator,
    PaginationParams,
)
from app.models.flag import (
    FlagResponse,
    FlagUpdateRequest,
    FlagStatusEnum,
    Flag,
)
from app.models.common import PaginatedResponse, Pagination
from app.models.user import User
from app.models.video import VideoID
from app.models.comment import CommentID
from app.services import flag_service, user_service, video_service, comment_service

router = APIRouter(prefix="/moderation", tags=["Moderation Actions"])


# Helper to construct paginated response consistently


def _build_paginated_flags(
    flags: List[FlagResponse] | List[Flag], total: int, pagination: PaginationParams
) -> PaginatedResponse[FlagResponse]:
    # Ensure each item is FlagResponse for strict model validation
    coerced: List[FlagResponse] = [
        item if isinstance(item, FlagResponse) else FlagResponse(**item.model_dump())  # type: ignore[arg-type]
        for item in flags
    ]
    total_pages = (total + pagination.pageSize - 1) // pagination.pageSize
    return PaginatedResponse[FlagResponse](  # type: ignore[misc]
        data=coerced,
        pagination=Pagination(
            currentPage=pagination.page,
            pageSize=pagination.pageSize,
            totalItems=total,
            totalPages=total_pages,
        ),
    )


@router.get(
    "/flags",
    response_model=PaginatedResponse[FlagResponse],
    summary="List all flags (moderator inbox)",
)
async def list_all_flags(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[FlagStatusEnum] = Query(
        None, alias="status", description="Filter by flag status"
    ),
    current_moderator: Annotated[User, Depends(get_current_moderator)] = None,
):
    flags, total = await flag_service.list_flags(
        page=pagination.page, page_size=pagination.pageSize, status_filter=status_filter
    )
    return _build_paginated_flags(flags, total, pagination)


@router.get(
    "/flags/{flag_id_path:uuid}",
    response_model=FlagResponse,
    summary="Get details of a specific flag",
)
async def get_flag_details(
    flag_id_path: UUID,
    current_moderator: Annotated[User, Depends(get_current_moderator)],
):
    flag = await flag_service.get_flag_by_id(flag_id=flag_id_path)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found"
        )
    return flag


@router.post(
    "/flags/{flag_id_path:uuid}/action",
    response_model=FlagResponse,
    summary="Take action on a specific flag",
)
async def act_on_flag(
    flag_id_path: UUID,
    action_request: FlagUpdateRequest,
    current_moderator: Annotated[User, Depends(get_current_moderator)],
):
    flag_obj = await flag_service.get_flag_by_id(flag_id=flag_id_path)
    if flag_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found"
        )

    if flag_obj.status not in {FlagStatusEnum.OPEN, FlagStatusEnum.UNDER_REVIEW}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Flag already resolved"
        )

    updated_flag = await flag_service.action_on_flag(
        flag_to_action=flag_obj,
        new_status=action_request.status,
        moderator_notes=action_request.moderatorNotes,
        moderator=current_moderator,
    )
    return updated_flag


@router.get(
    "/users",
    response_model=List[User],
    summary="Search for users (moderator only)",
)
async def search_users_endpoint(
    search_query: Optional[str] = Query(None, alias="q", description="Search text"),
    current_moderator: Annotated[User, Depends(get_current_moderator)] = None,
):
    return await user_service.search_users(query=search_query)


@router.post(
    "/users/{user_id_path:uuid}/assign-moderator",
    response_model=User,
    summary="Promote user to moderator",
)
async def assign_moderator_endpoint(
    user_id_path: UUID,
    current_moderator: Annotated[User, Depends(get_current_moderator)],
):
    updated = await user_service.assign_role_to_user(user_id_path, "moderator")
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return updated


@router.post(
    "/users/{user_id_path:uuid}/revoke-moderator",
    response_model=User,
    summary="Demote user from moderator",
)
async def revoke_moderator_endpoint(
    user_id_path: UUID,
    current_moderator: Annotated[User, Depends(get_current_moderator)],
):
    updated = await user_service.revoke_role_from_user(user_id_path, "moderator")
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return updated


class ContentRestoreResponse(BaseModel):
    content_id: UUID
    content_type: str
    status_message: str


@router.post(
    "/videos/{video_id_path:uuid}/restore",
    response_model=ContentRestoreResponse,
    summary="Restore a soft-deleted video (stub)",
)
async def restore_video_endpoint(
    video_id_path: VideoID,
    current_moderator: Annotated[User, Depends(get_current_moderator)],
):
    success = await video_service.restore_video(video_id_path)
    msg = "initiated" if success else "failed"
    return ContentRestoreResponse(
        content_id=video_id_path, content_type="video", status_message=msg
    )


@router.post(
    "/comments/{comment_id_path:uuid}/restore",
    response_model=ContentRestoreResponse,
    summary="Restore a soft-deleted comment (stub)",
)
async def restore_comment_endpoint(
    comment_id_path: CommentID,
    current_moderator: Annotated[User, Depends(get_current_moderator)],
):
    success = await comment_service.restore_comment(comment_id_path)
    msg = "initiated" if success else "failed"
    return ContentRestoreResponse(
        content_id=comment_id_path, content_type="comment", status_message=msg
    )
