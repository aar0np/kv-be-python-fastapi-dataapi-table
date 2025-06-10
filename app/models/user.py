from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    firstname: str = Field(..., min_length=1, max_length=50, alias="firstName")
    lastname: str = Field(..., min_length=1, max_length=50, alias="lastName")
    email: EmailStr


class UserCreateRequest(UserBase):
    password: str = Field(..., min_length=8)


class UserCreateResponse(UserBase):
    userid: UUID = Field(..., alias="userId")


class User(UserBase):
    model_config = ConfigDict(populate_by_name=True)

    userid: UUID = Field(..., alias="userId")
    created_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="createdDate"
    )
    account_status: str = Field(default="active", alias="accountStatus")
    last_login_date: Optional[datetime] = Field(None, alias="lastLoginDate")
    roles: List[str] = []  # Populated from token, not from DB

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def userId(self) -> UUID:  # noqa: N802 – keep camelCase for backward-compat
        """Return the camelCase alias for ``userid``.

        Several service layers (and older tests) still access the Pydantic
        ``User`` model using the original camel-cased attribute name
        ``userId``.  Accessing aliases directly via attribute lookup is not
        supported by Pydantic v2, therefore we expose this thin compatibility
        property so existing code keeps working while we progressively migrate
        everything to the canonical snake_case field ``userid``.
        """

        return self.userid


class UserCredentials(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str
    userid: UUID
    account_locked: bool = Field(False, alias="accountLocked")


# New Models for Login
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserLoginResponse(BaseModel):
    token: str
    user: User  # The existing User model


# New Model for Profile Update
class UserProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    firstname: Optional[str] = Field(
        None, min_length=1, max_length=50, alias="firstName"
    )
    lastname: Optional[str] = Field(None, min_length=1, max_length=50, alias="lastName")
