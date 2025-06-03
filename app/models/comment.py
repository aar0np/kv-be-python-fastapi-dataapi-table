"""Pydantic models for video comments."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

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

    commentId: CommentID
    videoId: VideoID
    userId: UserID
    createdAt: datetime
    updatedAt: datetime
    sentiment: Optional[str] = None  # placeholder (positive/neutral/negative)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


class CommentResponse(Comment):
    """Alias for response model (identical to Comment)."""

    pass


__all__ = [
    "CommentID",
    "CommentBase",
    "CommentCreateRequest",
    "Comment",
    "CommentResponse",
] 