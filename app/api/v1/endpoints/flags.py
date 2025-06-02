from __future__ import annotations

"""API endpoints allowing viewers to flag videos or comments."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_current_viewer
from app.models.user import User
from app.models.flag import FlagCreateRequest, FlagResponse
from app.services import flag_service

router = APIRouter(prefix="/flags", tags=["Flags"])


@router.post(
    "",
    response_model=FlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Flag content (video or comment)",
)
async def submit_flag(
    request: FlagCreateRequest,
    current_user: Annotated[User, Depends(get_current_viewer)],
):
    """Create a new flag for the specified content."""

    return await flag_service.create_flag(request=request, current_user=current_user) 