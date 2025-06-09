"""Pydantic models for video comments."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

# Import centralized type aliases
from app.models.common import UserID, VideoID, CommentID


class CommentBase(BaseModel):
    """Fields common to comment creation and storage."""

    text: str = Field(..., min_length=1, max_length=1000)


class CommentCreateRequest(CommentBase):
    """Payload for creating a new comment."""

    pass


class Comment(CommentBase):
    """Persistent representation stored in DB and returned via API."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    commentid: CommentID = Field(..., alias="commentId")
    videoid: VideoID = Field(..., alias="videoId")
    userid: UserID = Field(..., alias="userId")
    comment: str = Field(..., alias="text")
    sentiment_score: Optional[float] = None

    # Optional metadata fields present in some API contexts/tests
    createdAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(), alias="created_at")
    updatedAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(), alias="updated_at")
    sentiment: Optional[str] = None  # Free-form sentiment label used by tests

    # ------------------------------------------------------------------
    # Compatibility helpers (camelCase attribute access)
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def videoId(self) -> VideoID:  # noqa: N802 – keep camelCase for backward-compat
        """Return the camelCase alias for ``videoid``.

        Prior test suites and service layers still access the ``Comment`` model
        via the camel-cased attribute name ``videoId``.  Pydantic v2 does **not**
        expose aliases through attribute access, therefore we add an explicit
        passthrough property so legacy references continue to work while we
        progressively migrate everything to the canonical snake_case field
        ``videoid``.
        """

        return self.videoid

    @property  # type: ignore[override]
    def commentId(self) -> CommentID:  # noqa: N802
        """Return the camelCase alias for ``commentid`` (see notes in ``videoId``)."""

        return self.commentid

    @property  # type: ignore[override]
    def userId(self) -> UserID:  # noqa: N802
        """Return the camelCase alias for ``userid`` (see notes in ``videoId``)."""

        return self.userid


class CommentResponse(BaseModel):
    """API response representation for a single comment."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    commentId: CommentID = Field(..., alias="commentid")
    videoId: VideoID = Field(..., alias="videoid")
    userId: UserID = Field(..., alias="userid")
    text: str = Field(..., alias="comment")
    sentimentScore: Optional[float] = Field(None, alias="sentiment_score")


__all__ = [
    "CommentID",
    "CommentBase",
    "CommentCreateRequest",
    "Comment",
    "CommentResponse",
]
