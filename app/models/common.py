from typing import List, TypeVar, Generic, Optional
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


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
