from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException

from app.models.recommendation import EmbeddingIngestRequest, EmbeddingIngestResponse
from app.models.user import User
from app.api.v1.dependencies import get_current_creator
from app.services import recommendation_service

router = APIRouter(prefix="/reco", tags=["Recommendations Internal"])


@router.post(
    "/ingest",
    response_model=EmbeddingIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest vector embedding for a video",
)
async def ingest_embedding(
    request: EmbeddingIngestRequest,
    current_user: Annotated[User, Depends(get_current_creator)],
):
    """Accept a vector embedding for a video (creator-only)."""

    response = await recommendation_service.ingest_video_embedding(request)

    if response.status == "error" and (response.message or "").startswith("Video"):
        # Normalise to HTTP 404 if video missing.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=response.message
        )

    return response
