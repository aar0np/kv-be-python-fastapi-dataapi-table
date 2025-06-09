from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from app.models.video import VideoID


class RecommendationItem(BaseModel):
    """Lightweight representation of a recommended video for list endpoints."""

    videoId: VideoID
    title: str
    thumbnailUrl: Optional[HttpUrl] = None
    # Optional relevance score between 0 and 1 returned if the backend is able
    # to compute it. For the current stub implementation this field will be
    # populated with a random value to help front-end developers integrate.
    score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Relevance score where 1 is most relevant.",
    )

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def videoid(self) -> VideoID:  # noqa: N802 – keep snake_case for compat
        """Alias for camelCase *videoId* to maintain test compatibility."""
        return self.videoId


__all__ = [
    "RecommendationItem",
    "EmbeddingIngestRequest",
    "EmbeddingIngestResponse",
]


# ---------------------------------------------------------------------------
# Vector Embedding ingestion
# ---------------------------------------------------------------------------


class EmbeddingIngestRequest(BaseModel):
    """Payload accepted by the vector‐embedding ingestion endpoint."""

    videoId: VideoID
    vector: list[float] = Field(
        ..., description="The vector embedding extracted from the video's content."
    )


class EmbeddingIngestResponse(BaseModel):
    """Simple acknowledgement returned after receiving an embedding."""

    videoId: VideoID
    status: str
    message: Optional[str] = None
