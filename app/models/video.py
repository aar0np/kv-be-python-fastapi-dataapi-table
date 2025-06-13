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

from pydantic import BaseModel, Field, HttpUrl, ConfigDict

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

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=3, max_length=100, alias="title")
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Submit request model – now allows the client to send the title
# ---------------------------------------------------------------------------


class VideoSubmitRequest(BaseModel):
    """Payload accepted by the *submit video* endpoint.

    The **title** is optional – if the client already looked it up via the
    preview endpoint it can pass it here so the user immediately sees the
    correct name instead of the temporary placeholder.
    """

    youtubeUrl: HttpUrl = Field(..., alias="youtubeUrl")
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150,
        alias="title",
        description="Optional video title obtained from the preview step.",
    )


class Video(VideoBase):
    """Full canonical representation of a video stored in the database."""

    model_config = ConfigDict(populate_by_name=True)

    videoid: VideoID = Field(default_factory=uuid4, alias="videoId")
    userid: UUID = Field(..., alias="userId")
    added_date: datetime = Field(..., alias="submittedAt")
    preview_image_location: Optional[HttpUrl] = Field(None, alias="thumbnailUrl")

    # Fields from schema
    location: str
    location_type: int
    content_features: Optional[List[float]] = None
    content_rating: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None

    # Fields not in schema, but in original model
    youtubeVideoId: Optional[str] = None
    updatedAt: Optional[datetime] = None
    status: VideoStatusEnum = VideoStatusEnum.PENDING
    # Persisted as ``views`` in the *videos* table but still exposed to
    # callers as ``viewCount`` for backward-compatibility.
    viewCount: int = Field(0, alias="views")
    averageRating: Optional[float] = None
    totalRatingsCount: int = 0
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


class VideoUpdateRequest(BaseModel):
    """Payload for partial updates to a video owned by the caller or a moderator."""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(
        default=None, min_length=3, max_length=100, alias="title"
    )
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

    model_config = ConfigDict(populate_by_name=True)

    videoid: VideoID = Field(..., alias="videoId")
    name: str = Field(..., alias="title")
    preview_image_location: Optional[HttpUrl] = Field(None, alias="thumbnailUrl")
    userid: UUID = Field(..., alias="userId")
    added_date: datetime = Field(..., alias="submittedAt")

    # Fields from latest_videos schema to be added for consistency
    content_rating: Optional[str] = None
    category: Optional[str] = None

    # Fields not in latest_videos schema
    # Same aliasing logic for the compact summary representation
    viewCount: int = Field(0, alias="views")
    averageRating: Optional[float] = None

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def videoId(self) -> VideoID:  # noqa: N802 – keep camelCase for backward-compat
        """Alias for the canonical ``videoid`` field (snake_case)."""
        return self.videoid

    @property  # type: ignore[override]
    def thumbnailUrl(self):  # noqa: N802
        """Alias for ``preview_image_location``."""
        return self.preview_image_location

    @property  # type: ignore[override]
    def title(self):  # noqa: N802
        """Alias for ``name`` – kept for compatibility with earlier code."""
        return self.name


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
# Preview model (title only)
# ---------------------------------------------------------------------------


class VideoPreviewResponse(BaseModel):
    """Response model used by the *preview* endpoint to pre-fill UI fields."""

    title: str


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
    "VideoPreviewResponse",
]

# Ensure the full Video model also exposes camelCase aliases where useful.

setattr(
    Video,  # type: ignore[arg-type]
    "videoId",
    property(lambda self: self.videoid),  # noqa: B023
)
