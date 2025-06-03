from typing import List, TypeVar, Generic, Optional
from pydantic import BaseModel, Field
from uuid import UUID

DataT = TypeVar("DataT")

# ---------------------------------------------------------------------------
# Universal ID aliases used across the domain models
# ---------------------------------------------------------------------------
UserID = UUID
VideoID = UUID
CommentID = UUID
FlagID = UUID

__all__ = [
    "ProblemDetail",
    "Pagination",
    "PaginatedResponse",
    "UserID",
    "VideoID",
    "CommentID",
    "FlagID",
]


class ProblemDetail(BaseModel):
    type: str = Field(default="about:blank")
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None


class Pagination(BaseModel):
    currentPage: int
    pageSize: int
    totalItems: int
    totalPages: int


class PaginatedResponse(BaseModel, Generic[DataT]):
    data: List[DataT]
    pagination: Pagination
