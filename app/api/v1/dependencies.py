from typing import Annotated, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import TokenPayload
from app.models.user import User
from app.models.video import Video, VideoID

# Import user_service with a try-except block to handle potential circular imports
# This is a common pattern if dependencies.py is imported by services or vice-versa indirectly.
# However, based on the plan, user_service is a direct dependency here.
from app.services import user_service, video_service


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/users/login",
    auto_error=False,  # Handle missing token manually for clearer error
)


async def get_current_user_token_payload(
    token: Annotated[Optional[str], Depends(reusable_oauth2)],
) -> TokenPayload:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        payload_dict = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # Validate expiration
        exp_timestamp = payload_dict.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            if exp_datetime < datetime.now(timezone.utc):
                raise ExpiredSignatureError("Token has expired")

        token_data = TokenPayload(**payload_dict)

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (JWTError, ValidationError) as e:  # Catch Pydantic validation errors too
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data


# get_current_user_from_token will be added after get_user_by_id_from_table is in user_service
async def get_current_user_from_token(
    payload: Annotated[TokenPayload, Depends(get_current_user_token_payload)],
) -> User:
    if payload.sub is None:
        # This case should ideally be caught by TokenPayload model validation if sub is not Optional,
        # or if it is, a presence check here is good.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: Subject missing",
        )

    try:
        user_id = UUID(str(payload.sub))  # Ensure payload.sub is valid UUID string
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: Subject is not a valid UUID",
        )

    user = await user_service.get_user_by_id_from_table(user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user

# --- RBAC Dependencies ---
def require_role(required_roles: List[str]):
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user_from_token)]
    ) -> User:
        if not current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no roles assigned",
            )
        
        # Check if the user has ANY of the required roles
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have any of the required roles: {required_roles}",
            )
        return current_user
    return role_checker

# Specific role dependencies (can be imported and used directly in path operations)
async def get_current_viewer(current_user: Annotated[User, Depends(require_role(["viewer", "creator", "moderator"]))]) -> User:
    return current_user

async def get_current_creator(current_user: Annotated[User, Depends(require_role(["creator", "moderator"]))]) -> User:
    return current_user

async def get_current_moderator(current_user: Annotated[User, Depends(require_role(["moderator"]))]) -> User:
    return current_user

# ---------------------------------------------------------------------------
# Video-specific dependency
# ---------------------------------------------------------------------------


async def get_video_for_owner_or_moderator_access(
    video_id_path: VideoID,
    current_user: Annotated[User, Depends(get_current_user_from_token)],
) -> Video:
    """Fetch a video and ensure caller is owner or moderator.

    Raises 404 if video not found and 403 if user lacks permission.
    """

    video = await video_service.get_video_by_id(video_id_path)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    is_owner = video.userId == current_user.userId
    is_moderator = "moderator" in current_user.roles
    if not (is_owner or is_moderator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have permission to modify this video")

    return video

# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------


class PaginationParams:
    """Common pagination parameters.

    FastAPI will resolve this via dependency injection allowing endpoints to
    accept `page` and `pageSize` query parameters.
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        pageSize: int = Query(
            settings.DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.MAX_PAGE_SIZE,
            description="Items per page",
        ),
    ) -> None:
        self.page = page
        self.pageSize = pageSize


common_pagination_params = Annotated[PaginationParams, Depends()]

# Optional auth dependency


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(reusable_oauth2)],
) -> Optional[User]:
    """Return User if valid token provided, otherwise None (no error)."""

    if token is None:
        return None

    try:
        payload_dict = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload_dict)
        if token_data.sub is None:
            return None
    except (JWTError, ValidationError):
        return None

    try:
        user_id = UUID(str(token_data.sub))
    except ValueError:
        return None

    return await user_service.get_user_by_id_from_table(user_id=user_id)
