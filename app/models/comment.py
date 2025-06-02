"""Pydantic models for video comments."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Avoid circular import issues by defining local aliases.
UserID = UUID  # TODO: move to common types module
VideoID = UUID
CommentID = UUID


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