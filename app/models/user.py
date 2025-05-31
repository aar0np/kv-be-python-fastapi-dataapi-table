from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=50)
    lastName: str = Field(..., min_length=1, max_length=50)
    email: EmailStr


class UserCreateRequest(UserBase):
    password: str = Field(..., min_length=8)


class UserCreateResponse(UserBase):
    userId: UUID


class User(UserBase):
    userId: UUID
    roles: List[str] = Field(default_factory=lambda: ["viewer"])


# New Models for Login
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserLoginResponse(BaseModel):
    token: str
    user: User  # The existing User model


# New Model for Profile Update
class UserProfileUpdateRequest(BaseModel):
    firstName: Optional[str] = Field(None, min_length=1, max_length=50)
    lastName: Optional[str] = Field(None, min_length=1, max_length=50)
