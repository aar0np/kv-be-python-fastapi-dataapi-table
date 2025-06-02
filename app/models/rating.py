"""Pydantic models for video rating domain."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.video import VideoID

UserID = UUID
RatingValue = int


class RatingBase(BaseModel):
    rating: RatingValue = Field(..., ge=1, le=5, description="Rating value 1-5")


class RatingCreateOrUpdateRequest(RatingBase):
    pass


class Rating(RatingBase):
    videoId: VideoID
    userId: UserID
    createdAt: datetime
    updatedAt: datetime


class RatingResponse(Rating):
    pass


class AggregateRatingResponse(BaseModel):
    videoId: VideoID
    averageRating: float | None = None
    totalRatingsCount: int = 0
    currentUserRating: RatingValue | None = None


__all__ = [
    "RatingCreateOrUpdateRequest",
    "Rating",
    "RatingResponse",
    "AggregateRatingResponse",
    "RatingValue",
] 