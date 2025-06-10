"""Pydantic models for video rating domain."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.video import VideoID
from app.models.common import UserID

RatingValue = int


class RatingBase(BaseModel):
    rating: RatingValue = Field(..., ge=1, le=5, description="Rating value 1-5")


class RatingCreateOrUpdateRequest(RatingBase):
    pass


class Rating(RatingBase):
    """Canonical rating representation stored in the DB.

    The camelCase names come from the original KillrVideo schema whereas the
    tests (and some newer code) rely on Pythonic snake_case.  To make both
    worlds happy we mark the canonical camelCase names and expose matching
    snake_case *aliases* via the ``Field`` definition.
    """

    model_config = ConfigDict(populate_by_name=True)

    videoId: VideoID = Field(..., alias="videoid")
    userId: UserID = Field(..., alias="userid")
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(), alias="created_at"
    )
    updatedAt: datetime = Field(
        default_factory=lambda: datetime.now(), alias="updated_at"
    )

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def videoid(self) -> VideoID:  # noqa: N802
        return self.videoId

    @property  # type: ignore[override]
    def userid(self) -> UserID:  # noqa: N802
        return self.userId


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
