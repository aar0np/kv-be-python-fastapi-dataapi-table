from __future__ import annotations

"""Pydantic models related to content flagging and moderation."""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Aliases (centralized)
# ---------------------------------------------------------------------------
from app.models.common import FlagID


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ContentTypeEnum(str, Enum):
    """Possible kinds of content that can be flagged."""

    VIDEO = "video"
    COMMENT = "comment"


class FlagReasonCodeEnum(str, Enum):
    """Standardized reasons a user can provide when flagging content."""

    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    HARASSMENT = "harassment"
    COPYRIGHT = "copyright"
    OTHER = "other"


class FlagStatusEnum(str, Enum):
    """Lifecycle states for the moderation flag itself."""

    OPEN = "open"  # Awaiting moderator review
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"  # Flag deemed valid and content actioned
    REJECTED = "rejected"  # Flag deemed invalid / no action needed


# ---------------------------------------------------------------------------
# Base models
# ---------------------------------------------------------------------------
class FlagBase(BaseModel):
    """Fields shared across flag representations."""

    contentType: ContentTypeEnum
    contentId: UUID  # Validation of type happens in service layer
    reasonCode: FlagReasonCodeEnum
    reasonText: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional free-form context supplied by the reporter.",
    )


class FlagCreateRequest(FlagBase):
    """Payload viewers submit when flagging content."""

    pass


class Flag(FlagBase):
    """Canonical persisted representation of a flag."""

    flagId: FlagID = Field(default_factory=uuid4)
    userId: UUID  # Reporter
    createdAt: datetime
    updatedAt: datetime
    status: FlagStatusEnum = FlagStatusEnum.OPEN
    moderatorId: Optional[UUID] = None  # Set once actioned
    moderatorNotes: Optional[str] = None
    resolvedAt: Optional[datetime] = None


class FlagResponse(Flag):
    """Alias used in API responses."""

    pass


class FlagUpdateRequest(BaseModel):
    """Payload moderators send when changing a flag's status."""

    status: FlagStatusEnum
    moderatorNotes: Optional[str] = Field(default=None, max_length=1000)


__all__ = [
    "FlagID",
    "ContentTypeEnum",
    "FlagReasonCodeEnum",
    "FlagStatusEnum",
    "FlagBase",
    "FlagCreateRequest",
    "Flag",
    "FlagResponse",
    "FlagUpdateRequest",
]
