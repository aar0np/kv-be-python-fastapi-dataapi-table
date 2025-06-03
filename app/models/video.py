"""Pydantic models representing Video domain entities used throughout the Video
Catalog feature set.

These models are intentionally kept free of any persistence-layer details so
that they can be re-used both by service logic and by FastAPI response /
request models.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

# ---------------------------------------------------------------------------
# Aliases (centralized)
# ---------------------------------------------------------------------------
from app.models.common import VideoID


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class VideoStatusEnum(str, Enum):
    """Possible processing states for a submitted video."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Base Models
# ---------------------------------------------------------------------------
class VideoBase(BaseModel):
    """Fields shared by all video representations exposed publicly."""

    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: List[str] = Field(default_factory=list)


class VideoSubmitRequest(BaseModel):
    """Payload accepted by the *submit video* endpoint."""

    youtubeUrl: HttpUrl = Field(..., alias="youtubeUrl")


class Video(VideoBase):
    """Full canonical representation of a video stored in the database."""

    videoId: VideoID = Field(default_factory=uuid4)
    userId: UUID  # uploader's ID
    youtubeVideoId: str
    submittedAt: datetime
    updatedAt: datetime
    status: VideoStatusEnum = VideoStatusEnum.PENDING
    thumbnailUrl: Optional[HttpUrl] = None
    viewCount: int = 0
    averageRating: Optional[float] = None
    totalRatingsCount: int = 0
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


class VideoUpdateRequest(BaseModel):
    """Payload for partial updates to a video owned by the caller or a moderator."""

    title: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[List[str]] = None


class VideoDetailResponse(Video):
    """Response model returned when fetching full video details."""

    pass


class VideoStatusResponse(BaseModel):
    """Response model that surfaces only the processing status."""

    videoId: VideoID
    status: VideoStatusEnum


class VideoSummary(BaseModel):
    """Smaller representation used in paginated lists (e.g., latest videos)."""

    videoId: VideoID
    title: str
    thumbnailUrl: Optional[HttpUrl] = None
    userId: UUID
    submittedAt: datetime
    viewCount: int = 0
    averageRating: Optional[float] = None


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------

class VideoRatingRequest(BaseModel):
    """Client payload for submitting a rating (1-5)."""

    rating: int = Field(..., ge=1, le=5)


class VideoRatingSummary(BaseModel):
    """Aggregated rating stats for a video."""

    videoId: VideoID
    averageRating: float
    ratingCount: int


# ---------------------------------------------------------------------------
# Tag suggestion
# ---------------------------------------------------------------------------

class TagSuggestion(BaseModel):
    tag: str


# ---------------------------------------------------------------------------
# dunder
# ---------------------------------------------------------------------------
__all__ = [
    "VideoID",
    "VideoStatusEnum",
    "VideoBase",
    "VideoSubmitRequest",
    "Video",
    "VideoUpdateRequest",
    "VideoDetailResponse",
    "VideoStatusResponse",
    "VideoSummary",
    "VideoRatingRequest",
    "VideoRatingSummary",
    "TagSuggestion",
] 