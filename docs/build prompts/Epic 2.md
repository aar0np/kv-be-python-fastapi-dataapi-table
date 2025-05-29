Okay, let's proceed to the next phase, which will focus on the **Video Catalog** functionalities. We'll build upon the foundation established in Phase 0 and Epic 1 (Account Management).

---

**Phase 1: Epic 2 - Video Catalog (Core Functionality)**
*Goal: Implement functionalities for users (creators) to submit videos, view video status, update video details, and for any user to view video details, latest videos, and videos by tag/uploader. This epic will introduce the "creator" role.*

  *   **Chunk 2.1: Video Models & "Creator" Role Setup**
      *   **Step 2.1.1:** Create `app/models/video.py`:
          *   Import `BaseModel, Field, HttpUrl` from `pydantic`, `Optional, List, Dict` from `typing`, `UUID, uuid4` from `uuid`, `datetime` from `datetime`.
          *   Define `VideoID = UUID`.
          *   Define `VideoStatusEnum(str, Enum)`: `PENDING = "PENDING"`, `PROCESSING = "PROCESSING"`, `READY = "READY"`, `ERROR = "ERROR"`.
          *   Define `class VideoBase(BaseModel)`: `title: str = Field(..., min_length=3, max_length=100)`, `description: Optional[str] = Field(None, max_length=1000)`, `tags: Optional[List[str]] = Field(default_factory=list)`.
          *   Define `class VideoSubmitRequest(BaseModel)`: `youtubeUrl: HttpUrl`.
          *   Define `class Video(VideoBase)`: `videoId: VideoID`, `userId: UUID` (uploader's ID), `youtubeVideoId: str`, `submittedAt: datetime`, `updatedAt: datetime`, `status: VideoStatusEnum = VideoStatusEnum.PENDING`, `thumbnailUrl: Optional[HttpUrl] = None`, `viewCount: int = 0`, `averageRating: Optional[float] = None`.
          *   Define `class VideoCreateInternal(Video)`: This will be used internally by the service for creating the full video document. (Could also just use `Video` if all fields are set at creation).
          *   Define `class VideoUpdateRequest(BaseModel)`: `title: Optional[str] = Field(None, min_length=3, max_length=100)`, `description: Optional[str] = Field(None, max_length=1000)`, `tags: Optional[List[str]] = None`.
          *   Define `class VideoDetailResponse(Video)`: (Can be same as `Video` for now).
          *   Define `class VideoStatusResponse(BaseModel)`: `videoId: VideoID`, `status: VideoStatusEnum`.
          *   Define `class VideoSummary(BaseModel)`: `videoId: VideoID`, `title: str`, `thumbnailUrl: Optional[HttpUrl] = None`, `userId: UUID` (uploader), `submittedAt: datetime`, `viewCount: int = 0`, `averageRating: Optional[float] = None`.
      *   **Step 2.1.2:** Modify `app/api/v1/dependencies.py`: Ensure `get_current_creator` dependency is correctly defined using `require_role(["creator", "moderator"])`.
      *   **Step 2.1.3:** Modify `app/services/user_service.py`:
          *   (Conceptual for now, will be implemented in Moderator Epic) Add placeholder functions like `assign_role_to_user(user_id: UUID, role: str)` and `revoke_role_from_user(user_id: UUID, role: str)`. For testing this epic, we might need a temporary way to give a test user the "creator" role, or assume a user used in tests already has it. For now, we will assume a test user can be manually given "creator" role for testing purposes (e.g., by modifying their DB record directly or during token generation for tests).
      *   **Step 2.1.4:** Tests:
          *   No direct tests for models, but these will be used in subsequent endpoint/service tests.
          *   Review existing RBAC tests to ensure they are robust enough to differentiate between viewer and (future) creator roles.

  *   **Chunk 2.2: Video Submission Endpoint (Creator Only)**
      *   **Step 2.2.1:** Create `app/api/v1/endpoints/video_catalog.py`:
          *   Import `APIRouter, Depends, HTTPException, status, BackgroundTasks` from `fastapi`.
          *   Import `VideoSubmitRequest, VideoDetailResponse, VideoStatusResponse` from `app.models.video`.
          *   Import `User` from `app.models.user`.
          *   Import `get_current_creator` from `app.api.v1.dependencies`.
          *   Import `Annotated` from `typing`.
          *   Initialize `router = APIRouter(prefix="/videos", tags=["Videos"])`.
      *   **Step 2.2.2:** Create `app/services/video_service.py`:
          *   Import `Optional, Dict, Any, List` from `typing`, `UUID, uuid4` from `uuid`, `datetime, timezone` from `datetime`.
          *   Import `get_table` from `app.db.astra_client` and `AstraDBCollection` from `astrapy.db`.
          *   Import `VideoSubmitRequest, Video, VideoStatusEnum, VideoID` from `app.models.video`.
          *   Import `User` from `app.models.user`.
          *   Define `VIDEOS_TABLE_NAME: str = "videos"`.
          *   Implement `def extract_youtube_video_id(youtube_url: str) -> Optional[str]`: A helper to parse YouTube video ID from various URL formats (a common utility, can be simple for now).
          *   Implement `async def submit_new_video(request: VideoSubmitRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Video`:
              *   Calls `extract_youtube_video_id`. If invalid, raise `HTTPException 400`.
              *   Constructs a `Video` document/Pydantic model: `videoId=uuid4()`, `userId=current_user.userId`, `youtubeVideoId`, `submittedAt=datetime.now(timezone.utc)`, `updatedAt=datetime.now(timezone.utc)`, `status=VideoStatusEnum.PENDING`, `title="Pending Title"`, other fields default or None. (Title/description will be fetched later).
              *   Saves to `VIDEOS_TABLE_NAME` using `db_table.insert_one()`.
              *   Returns the created `Video` Pydantic model.
          *   Implement (stub for now) `async def process_video_submission(video_id: VideoID, youtube_video_id: str)`:
              *   `# TODO: Fetch video details (title, description, thumbnail) from YouTube API.`
              *   `# TODO: Generate embeddings (if applicable).`
              *   `# TODO: Update video record in DB with details and set status to PROCESSING, then READY or ERROR.`
              *   For now, it can just log: `print(f"Background task: Processing video {video_id} with YouTube ID {youtube_video_id}")`.
      *   **Step 2.2.3:** In `video_catalog.py`, implement `POST /` endpoint (maps to `/videos`):
          *   Path operation: `@router.post("/", response_model=VideoDetailResponse, status_code=status.HTTP_202_ACCEPTED, summary="Submit YouTube URL (async processing)")`.
          *   Protected by `current_user: Annotated[User, Depends(get_current_creator)]`.
          *   Takes `request: VideoSubmitRequest` and `background_tasks: BackgroundTasks` as input.
          *   Calls `new_video = await video_service.submit_new_video(request, current_user)`.
          *   Adds a background task: `background_tasks.add_task(video_service.process_video_submission, new_video.videoId, new_video.youtubeVideoId)`.
          *   Returns `new_video` (as `VideoDetailResponse`).
      *   **Step 2.2.4:** Modify `app/main.py` (or service-specific entrypoint): Include `video_catalog.router`.
      *   **Step 2.2.5:** Tests:
          *   Write unit tests for `video_service.extract_youtube_video_id`.
          *   Write unit tests for `video_service.submit_new_video` (mock DB calls).
          *   Write unit tests for `video_service.process_video_submission` (for now, just check it can be called).
          *   Create `tests/api/v1/endpoints/test_video_catalog.py`. Write integration tests for `POST /videos`:
              *   Mock `video_service.submit_new_video` and `background_tasks.add_task`.
              *   Test successful submission with a "creator" token.
              *   Test with a "viewer" token (expect 403).
              *   Test with invalid YouTube URL (mock service to raise HTTP 400).

  *   **Chunk 2.3: Video Status & Get Video Details Endpoints**
      *   **Step 2.3.1:** In `video_service.py`:
          *   Implement `async def get_video_by_id(video_id: VideoID, db_table: Optional[AstraDBCollection] = None) -> Optional[Video]`: Fetches video by `videoId` from DB and maps to `Video` model.
      *   **Step 2.3.2:** In `video_catalog.py`:
          *   Implement `GET /videos/{videoId}/status` endpoint:
              *   Path operation: `@router.get("/{video_id}/status", response_model=VideoStatusResponse, summary="Processing status")`.
              *   `video_id: VideoID` as path parameter.
              *   Protected by `current_user: Annotated[User, Depends(get_current_creator)]` (or `get_current_viewer` if status is public for uploader - API spec says creator/moderator). Let's stick to creator/moderator.
              *   Calls `video = await video_service.get_video_by_id(video_id)`. If not found, `HTTPException 404`.
              *   (RBAC check: if `video.userId != current_user.userId` AND "moderator" not in `current_user.roles`, raise `HTTPException 403`).
              *   Returns `VideoStatusResponse(videoId=video.videoId, status=video.status)`.
          *   Implement `GET /videos/{videoId}` endpoint:
              *   Path operation: `@router.get("/{video_id}", response_model=VideoDetailResponse, summary="Video details")`.
              *   `video_id: VideoID` as path parameter.
              *   This endpoint is public (no auth decorator).
              *   Calls `video = await video_service.get_video_by_id(video_id)`. If not found, `HTTPException 404`.
              *   If `video.status != VideoStatusEnum.READY` (and user is not owner/moderator), potentially raise 404 or return a limited response (API spec implies public if it exists). For now, return if found, regardless of status, for simplicity.
              *   Returns the `video` object (as `VideoDetailResponse`).
      *   **Step 2.3.3:** Tests:
          *   Write unit tests for `video_service.get_video_by_id`.
          *   Update integration tests in `test_video_catalog.py`:
              *   Test `GET /videos/{videoId}/status`:
                  *   With creator token (owner).
                  *   With creator token (not owner, expect 403 if strict RBAC).
                  *   With viewer token (expect 403).
                  *   Video not found.
              *   Test `GET /videos/{videoId}`:
                  *   Video found and public.
                  *   Video not found.

  *   **Chunk 2.4: Update Video Details Endpoint (Owner/Moderator)**
      *   **Step 2.4.1:** In `app/api/v1/dependencies.py`:
          *   Define a more complex dependency `async def get_video_for_owner_or_moderator_access(video_id: VideoID, current_user: Annotated[User, Depends(get_current_user_from_token)]) -> Video`:
              *   Fetches video using `video_service.get_video_by_id(video_id)`. If not found, `HTTPException 404`.
              *   Checks if `current_user.userId == video.userId` OR `"moderator" in current_user.roles`.
              *   If neither, raise `HTTPException 403`.
              *   Returns the `video` object.
      *   **Step 2.4.2:** In `video_service.py`:
          *   Implement `async def update_video_details(video: Video, update_request: VideoUpdateRequest, db_table: Optional[AstraDBCollection] = None) -> Video`:
              *   Takes existing `Video` object and `VideoUpdateRequest`.
              *   Constructs `update_fields = update_request.model_dump(exclude_unset=True)`.
              *   If `update_fields` is not empty:
                  *   Adds `updatedAt=datetime.now(timezone.utc)` to `update_fields`.
                  *   Calls `db_table.update_one(filter={"videoId": str(video.videoId)}, update={"$set": update_fields})`.
                  *   Refetches/updates the input `video` object with `update_fields` and new `updatedAt`.
              *   Returns the (potentially updated) `video` object.
      *   **Step 2.4.3:** In `video_catalog.py`:
          *   Implement `PUT /videos/{videoId}` endpoint:
              *   Path operation: `@router.put("/{video_id}", response_model=VideoDetailResponse, summary="Update details")`.
              *   Takes `update_request: VideoUpdateRequest`.
              *   Protected by `video_to_update: Annotated[Video, Depends(get_video_for_owner_or_moderator_access)]` (where `video_id` from path is implicitly passed to the dependency).
              *   Calls `updated_video = await video_service.update_video_details(video=video_to_update, update_request=update_request)`.
              *   Returns `updated_video`.
      *   **Step 2.4.4:** Tests:
          *   Write unit tests for `dependencies.get_video_for_owner_or_moderator_access` (mock service calls).
          *   Write unit tests for `video_service.update_video_details`.
          *   Update integration tests in `test_video_catalog.py`:
              *   Test `PUT /videos/{videoId}`:
                  *   With owner token.
                  *   With moderator token (needs a way to designate a test user as moderator).
                  *   With non-owner/non-moderator creator token (expect 403).
                  *   With viewer token (expect 401/403 from outer auth).
                  *   Video not found (expect 404 from dependency).

  *   **Chunk 2.5: Record Video View & List Endpoints (Latest, By Tag, By User)**
      *   **Step 2.5.1:** In `video_service.py`:
          *   Implement `async def record_video_view(video_id: VideoID, db_table: Optional[AstraDBCollection] = None) -> bool`:
              *   Fetches video. If not found, return `False`.
              *   Increments `viewCount` using `db_table.update_one(filter={"videoId": str(video_id)}, update={"$inc": {"viewCount": 1}})`. (Note: `$inc` is a MongoDB operator; check `astrapy` equivalent for atomic increment or do read-modify-write if not directly supported by Data API in one op). For `astrapy` with Data API, it might be find, increment in Python, then update.
              *   Return `True` if update was successful.
          *   Implement `async def list_latest_videos(page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
              *   Queries `VIDEOS_TABLE_NAME` for videos where `status == VideoStatusEnum.READY`.
              *   Sorts by `submittedAt` descending. Implements pagination (skip, limit).
              *   Maps results to `VideoSummary` model.
              *   Returns list of summaries and total count of ready videos.
          *   Implement `async def list_videos_by_tag(tag: str, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
              *   Queries for videos where `status == VideoStatusEnum.READY` and `tags` array contains `tag`. (Check `astrapy` for array contains query).
              *   Sorts by `submittedAt` descending. Implements pagination.
              *   Maps to `VideoSummary`. Returns list and total count.
          *   Implement `async def list_videos_by_user(user_id: UUID, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
              *   Queries for videos where `userId == user_id` (and optionally `status == VideoStatusEnum.READY` if only ready videos are public for other users).
              *   Sorts by `submittedAt` descending. Implements pagination.
              *   Maps to `VideoSummary`. Returns list and total count.
      *   **Step 2.5.2:** In `app/api/v1/dependencies.py`:
          *   Define `class PaginationParams` and `common_pagination_params = Annotated[PaginationParams, Depends()]` as shown in original Build Spec. (Add to `app/core/config.py`: `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`).
      *   **Step 2.5.3:** In `video_catalog.py`:
          *   Import `VideoSummary`, `PaginatedResponse`, `Pagination` from `app.models.common` and `app.models.video`.
          *   Import `common_pagination_params`, `PaginationParams` from `app.api.v1.dependencies`.
          *   Import `UUID` from `uuid`.
          *   Implement `POST /videos/{videoId}/view` endpoint:
              *   Path operation: `@router.post("/{video_id}/view", status_code=status.HTTP_204_NO_CONTENT, summary="Record playback view")`. Public.
              *   Calls `video = await video_service.get_video_by_id(video_id)`. If not found or not `READY`, `HTTPException 404`.
              *   Calls `await video_service.record_video_view(video_id)`.
              *   Returns `Response(status_code=status.HTTP_204_NO_CONTENT)`.
          *   Implement `GET /videos/latest` endpoint:
              *   Path operation: `@router.get("/latest", response_model=PaginatedResponse[VideoSummary], summary="Latest videos")`. Public.
              *   Takes `pagination: Annotated[PaginationParams, Depends(common_pagination_params)]`.
              *   Calls `video_service.list_latest_videos`.
              *   Constructs and returns `PaginatedResponse`.
          *   Implement `GET /videos/by-tag/{tag}` endpoint:
              *   Path operation: `@router.get("/by-tag/{tag}", response_model=PaginatedResponse[VideoSummary], summary="Videos by tag")`. Public.
              *   Takes `tag: str` and `pagination: Annotated[PaginationParams, Depends(common_pagination_params)]`.
              *   Calls `video_service.list_videos_by_tag`. Returns `PaginatedResponse`.
          *   Implement `GET /users/{userId}/videos` endpoint (note: this is under `/users` prefix in API spec, but logically related to videos. For now, place in `video_catalog.py` for simplicity, or create a small `users_related_router.py` later).
              *   Path operation: `@router.get("/by-uploader/{user_id}", response_model=PaginatedResponse[VideoSummary], summary="Videos by uploader")` (adjust path for clarity if kept in video_catalog or move to a user-centric router). The OpenAPI spec shows `/users/{userId}/videos` which would mean it belongs in a router handling `/users`. Let's assume for now it's added to `account_management.py` router or a new user-centric router for better path alignment.
              *   For now, as a simpler step if adding to `video_catalog.py`: `@router.get("/by-user/{user_id}", response_model=PaginatedResponse[VideoSummary], summary="Videos by uploader")`
              *   Takes `user_id: UUID` and `pagination: Annotated[PaginationParams, Depends(common_pagination_params)]`.
              *   Calls `video_service.list_videos_by_user`. Returns `PaginatedResponse`.
      *   **Step 2.5.4:** Tests:
          *   Write unit tests for all new `video_service` functions. Pay attention to pagination and sorting logic. Mock DB queries.
          *   Update integration tests in `test_video_catalog.py`:
              *   Test `POST /videos/{videoId}/view`.
              *   Test `GET /videos/latest` with and without pagination params.
              *   Test `GET /videos/by-tag/{tag}`.
              *   Test `GET /videos/by-user/{user_id}` (or its final path).

---

This completes the detailed plan for Epic 2: Video Catalog (Core). I'll now generate the LLM prompts for this epic.

## LLM Prompts - Iteration 2 (Epic 2: Video Catalog - Core)

---
**Prompt 9 (was 2.1): Video Models & Creator Role Setup**
```text
Objective: Define Pydantic models for Video entities and ensure the "creator" role concept is integrated into dependencies for future use.

Specifications:
1.  Create `app/models/video.py`:
    *   Import `BaseModel, Field, HttpUrl` from `pydantic`, `Optional, List, Dict, Tuple` from `typing`, `UUID, uuid4` from `uuid`, `datetime` from `datetime`, and `Enum` from `enum`.
    *   Define `VideoID = UUID`.
    *   Define `class VideoStatusEnum(str, Enum)`: `PENDING = "PENDING"`, `PROCESSING = "PROCESSING"`, `READY = "READY"`, `ERROR = "ERROR"`.
    *   Define `class VideoBase(BaseModel)`: `title: str = Field(..., min_length=3, max_length=100)`, `description: Optional[str] = Field(None, max_length=1000)`, `tags: List[str] = Field(default_factory=list)`.
    *   Define `class VideoSubmitRequest(BaseModel)`: `youtubeUrl: HttpUrl`.
    *   Define `class Video(VideoBase)`: `videoId: VideoID`, `userId: UUID` (uploader's ID), `youtubeVideoId: str`, `submittedAt: datetime`, `updatedAt: datetime`, `status: VideoStatusEnum = VideoStatusEnum.PENDING`, `thumbnailUrl: Optional[HttpUrl] = None`, `viewCount: int = 0`, `averageRating: Optional[float] = None`.
    *   Define `class VideoUpdateRequest(BaseModel)`: `title: Optional[str] = Field(None, min_length=3, max_length=100)`, `description: Optional[str] = Field(None, max_length=1000)`, `tags: Optional[List[str]] = None`.
    *   Define `class VideoDetailResponse(Video)`: (This can be an alias or inherit directly: `pass`).
    *   Define `class VideoStatusResponse(BaseModel)`: `videoId: VideoID`, `status: VideoStatusEnum`.
    *   Define `class VideoSummary(BaseModel)`: `videoId: VideoID`, `title: str`, `thumbnailUrl: Optional[HttpUrl] = None`, `userId: UUID`, `submittedAt: datetime`, `viewCount: int = 0`, `averageRating: Optional[float] = None`.
2.  Modify `app/api/v1/dependencies.py`:
    *   Ensure the `get_current_creator` dependency is correctly defined using `require_role(["creator", "moderator"])` which was introduced in Prompt 8.
    *   (No new code here, just verification of the existing `get_current_creator` from previous work on RBAC).
3.  For testing purposes, we need a way to identify a user as a "creator". For now, assume that when a JWT is generated for tests requiring a "creator", the `roles` claim in the token will include "creator". This will be handled in the test setup code that generates tokens, not in the main application logic for this prompt.

Current Files to Work On:
*   `app/models/video.py`
*   `app/api/v1/dependencies.py` (Verification)

Provide the complete content for `app/models/video.py`.
```
---
**Prompt 10 (was 2.2): Video Submission Endpoint (Creator Only)**
```text
Objective: Implement the video submission endpoint, accessible only by users with the "creator" role. This involves creating a video service, a new API router, and handling asynchronous background tasks for future processing.

Specifications:
1.  Create `app/services/video_service.py`:
    *   Import `Optional, Dict, Any, List` from `typing`, `UUID, uuid4` from `uuid`, `datetime, timezone` from `datetime`, `re` for regex.
    *   Import `get_table` from `app/db/astra_client` and `AstraDBCollection` from `astrapy.db`.
    *   Import `VideoSubmitRequest, Video, VideoStatusEnum, VideoID, VideoBase` from `app/models/video`. (VideoBase might not be needed directly here yet).
    *   Import `User` from `app.models.user`.
    *   Import `HTTPException, status` from `fastapi`.
    *   Define `VIDEOS_TABLE_NAME: str = "videos"` as a constant.
    *   Implement `def extract_youtube_video_id(youtube_url: str) -> Optional[str]`:
        *   Uses regex to extract the video ID from various YouTube URL formats (e.g., `youtube.com/watch?v=VIDEO_ID`, `youtu.be/VIDEO_ID`, `youtube.com/embed/VIDEO_ID`).
        *   Return the video ID string if found, else `None`.
    *   Implement `async def submit_new_video(request: VideoSubmitRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Video`:
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   Call `youtube_id = extract_youtube_video_id(str(request.youtubeUrl))`. If `youtube_id` is None, raise `HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid YouTube URL or unable to extract video ID")`.
        *   Construct `video_data_dict`: `videoId=uuid4()`, `userId=current_user.userId`, `youtubeVideoId=youtube_id`, `submittedAt=datetime.now(timezone.utc)`, `updatedAt=datetime.now(timezone.utc)`, `status=VideoStatusEnum.PENDING`, `title="Video Title Pending Processing"`, `description=None`, `tags=[]`, `thumbnailUrl=None`, `viewCount=0`, `averageRating=None`.
        *   Create a `Video` Pydantic model instance: `new_video_obj = Video(**video_data_dict)`.
        *   Convert `new_video_obj.model_dump(by_alias=True)` (use `by_alias=True` if your Pydantic models use aliases for DB field names, otherwise not needed) to a dictionary for insertion. Ensure `videoId` and `userId` are stored as strings if your DB requires it (e.g. `str(new_video_obj.videoId)`). Let's assume UUIDs are stored as strings for AstraDB JSON. So, `video_doc_to_insert = new_video_obj.model_dump()` but convert UUID fields to `str()`.
        *   Call `await db_table.insert_one(document=video_doc_to_insert)`.
        *   Return `new_video_obj`.
    *   Implement `async def process_video_submission(video_id: VideoID, youtube_video_id: str)`:
        *   For now, simply log using `print(f"BACKGROUND TASK: Processing video {video_id} for YouTube ID {youtube_video_id}. TODO: Implement actual processing.")`.
2.  Create `app/api/v1/endpoints/video_catalog.py`:
    *   Import `APIRouter, Depends, HTTPException, status, BackgroundTasks` from `fastapi`.
    *   Import `VideoSubmitRequest, VideoDetailResponse` from `app/models/video` (VideoStatusResponse not needed yet).
    *   Import `User` from `app/models.user`.
    *   Import `get_current_creator` from `app/api/v1/dependencies`.
    *   Import `video_service` from `app.services`.
    *   Import `Annotated` from `typing`.
    *   Initialize `router = APIRouter(prefix="/videos", tags=["Videos"])`.
    *   Implement `POST /` endpoint (path will be `/` relative to router prefix):
        *   Decorator: `@router.post("/", response_model=VideoDetailResponse, status_code=status.HTTP_202_ACCEPTED, summary="Submit YouTube URL (async processing)")`.
        *   Signature: `async def submit_video(request: VideoSubmitRequest, background_tasks: BackgroundTasks, current_user: Annotated[User, Depends(get_current_creator)])`.
        *   Call `new_video = await video_service.submit_new_video(request=request, current_user=current_user)`.
        *   Add background task: `background_tasks.add_task(video_service.process_video_submission, new_video.videoId, new_video.youtubeVideoId)`.
        *   Return `new_video`.
3.  Modify `app/main.py` (or your main monolith entrypoint):
    *   Import `video_catalog_router` from `app.api.v1.endpoints.video_catalog` (rename `router` in `video_catalog.py` to avoid name clashes).
    *   Include it in `api_router_v1`: `api_router_v1.include_router(video_catalog.router)`.
4.  Create `tests/services/test_video_service.py`:
    *   Write unit tests for `extract_youtube_video_id` with various valid and invalid URLs.
    *   Write unit tests for `submit_new_video`:
        *   Mock `get_table` and `AstraDBCollection.insert_one`.
        *   Test successful submission. Verify data passed to `insert_one`.
        *   Test invalid YouTube URL (mock `extract_youtube_video_id` to return `None`).
    *   Test `process_video_submission` (for now, just ensure it can be called, perhaps mock `print`).
5.  Create `tests/api/v1/endpoints/test_video_catalog.py`:
    *   Import `AsyncClient`, `status`, `User`, `Video`.
    *   Helper function to create JWT for a test user, now with an option to include "creator" in roles.
    *   Write integration tests for `POST /api/v1/videos/`:
        *   Mock `video_service.submit_new_video` to return a sample `Video` object.
        *   Mock `BackgroundTasks.add_task`.
        *   Test successful submission (202) with a "creator" token. Verify `add_task` was called.
        *   Test submission with a "viewer" token (expect 403 Forbidden). This requires `get_current_creator` to correctly use `require_role`.
        *   Test submission with no token (expect 401 Unauthorized from `reusable_oauth2` if `auto_error=True`, or from our manual check in `get_current_user_token_payload` if `auto_error=False`).
        *   Test with invalid YouTube URL (mock `video_service.submit_new_video` to raise the specific `HTTPException(400)`).

Current Files to Work On:
*   `app/services/video_service.py`
*   `app/api/v1/endpoints/video_catalog.py`
*   `app/main.py`
*   `tests/services/test_video_service.py`
*   `tests/api/v1/endpoints/test_video_catalog.py`

Provide the complete content for each new/modified file. Remember to handle UUIDs as strings for DB storage where appropriate in the service layer.
```
---
**Prompt 11 (was 2.3): Video Status & Get Video Details Endpoints**
```text
Objective: Implement endpoints for retrieving a video's processing status (for creators/moderators) and its full details (publicly).

Specifications:
1.  Modify `app/services/video_service.py`:
    *   Import `VideoID, Video, VideoStatusResponse, VideoStatusEnum` (VideoStatusResponse may not be needed in service).
    *   Implement `async def get_video_by_id(video_id: VideoID, db_table: Optional[AstraDBCollection] = None) -> Optional[Video]`:
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   Fetches video document by `videoId` (querying `str(video_id)`).
        *   If found, maps the document dictionary to a `Video` Pydantic model and returns it. Ensure `userId` and `videoId` are converted back to `UUID` if stored as strings.
        *   If not found, returns `None`.
2.  Modify `app/api/v1/endpoints/video_catalog.py`:
    *   Import `VideoStatusResponse, VideoID, VideoStatusEnum, Video` from `app/models/video`.
    *   Import `get_current_user_from_token` from `app.api.v1.dependencies` (as `get_current_creator` might be too restrictive for some owner checks if not also a moderator, and `get_current_user_from_token` gives us the base user to check roles and ID).
    *   Implement `GET /{video_id}/status` endpoint:
        *   Decorator: `@router.get("/{video_id_path}/status", response_model=VideoStatusResponse, summary="Processing status")`. Use `video_id_path: VideoID` to avoid conflict if `video_id` is used as a variable name.
        *   Signature: `async def get_video_status(video_id_path: VideoID, current_user: Annotated[User, Depends(get_current_user_from_token)])`. (Using `get_current_user_from_token` to get user, then checking roles/ownership manually).
        *   Call `video = await video_service.get_video_by_id(video_id=video_id_path)`.
        *   If not `video`, raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")`.
        *   RBAC Check: `is_owner = video.userId == current_user.userId`. `is_moderator = "moderator" in current_user.roles`. `is_creator_self = "creator" in current_user.roles and is_owner`. Per API spec "creator / moderator": if not (`is_creator_self` or `is_moderator`), raise `HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have permission to view status of this video")`.
        *   Return `VideoStatusResponse(videoId=video.videoId, status=video.status)`.
    *   Implement `GET /{video_id}` endpoint (public):
        *   Decorator: `@router.get("/{video_id_path}", response_model=VideoDetailResponse, summary="Video details")`.
        *   Signature: `async def get_video_details(video_id_path: VideoID)`.
        *   Call `video = await video_service.get_video_by_id(video_id=video_id_path)`.
        *   If not `video`, raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")`.
        *   Optional: If `video.status != VideoStatusEnum.READY`, you might choose to still return 404 for non-owners/moderators, or return it as is. API spec implies it's public if it exists. For now, return if found.
        *   Return `video`.
3.  In `tests/services/test_video_service.py`:
    *   Write unit tests for `get_video_by_id`.
    *   Mock DB calls. Test found and not found scenarios.
    *   Ensure correct mapping from DB doc to `Video` model, including UUID conversions.
4.  In `tests/api/v1/endpoints/test_video_catalog.py`:
    *   Add tests for `GET /api/v1/videos/{video_id}/status`:
        *   Mock `video_service.get_video_by_id`.
        *   Provide a helper to generate tokens with specific roles ("creator", "moderator", "viewer") and user IDs.
        *   Test as video owner (creator).
        *   Test as non-owner creator (expect 403).
        *   Test as moderator (not owner).
        *   Test as viewer (expect 403).
        *   Test video not found (expect 404).
    *   Add tests for `GET /api/v1/videos/{video_id}`:
        *   Mock `video_service.get_video_by_id`.
        *   Test video found (public access, no token needed or with any token).
        *   Test video not found (expect 404).
        *   Test with videos in different statuses (e.g., PENDING, READY) to ensure they are returned.

Current Files to Work On:
*   `app/services/video_service.py`
*   `app/api/v1/endpoints/video_catalog.py`
*   `tests/services/test_video_service.py`
*   `tests/api/v1/endpoints/test_video_catalog.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 12 (was 2.4): Update Video Details Endpoint (Owner/Moderator)**
```text
Objective: Implement an endpoint for video owners or moderators to update video details like title, description, and tags.

Specifications:
1.  Modify `app/api/v1/dependencies.py`:
    *   Import `Video, VideoID` from `app/models/video`.
    *   Import `video_service` from `app/services`. (If not already imported for other dependencies).
    *   Implement `async def get_video_for_owner_or_moderator_access(video_id_path: VideoID, current_user: Annotated[User, Depends(get_current_user_from_token)]) -> Video`:
        *   (Path parameter name `video_id_path` used to avoid conflict if `video_id` used in signature).
        *   Fetches `video = await video_service.get_video_by_id(video_id=video_id_path)`. If not found, raise `HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")`.
        *   Check ownership: `is_owner = video.userId == current_user.userId`.
        *   Check if moderator: `is_moderator = "moderator" in current_user.roles`.
        *   If not (`is_owner` or `is_moderator`), raise `HTTPException(status.HTTP_403_FORBIDDEN, "User does not have permission to modify this video")`.
        *   Return `video`.
2.  Modify `app/services/video_service.py`:
    *   Import `VideoUpdateRequest, Video` from `app/models/video`.
    *   Import `datetime, timezone` from `datetime`.
    *   Implement `async def update_video_details(video_to_update: Video, update_request: VideoUpdateRequest, db_table: Optional[AstraDBCollection] = None) -> Video`:
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   `update_fields = update_request.model_dump(exclude_unset=True)`.
        *   If `update_fields`:
            *   Add `updatedAt = datetime.now(timezone.utc)` to `update_fields`.
            *   `await db_table.update_one(filter={"videoId": str(video_to_update.videoId)}, update={"$set": update_fields})`.
            *   Create a new `Video` object by taking `video_to_update.model_dump()` and updating it with `update_fields`: `updated_video_data = {**video_to_update.model_dump(), **update_fields}`.
            *   `return Video(**updated_video_data)`.
        *   Else (no fields to update):
            *   Return `video_to_update` (the original object).
3.  Modify `app/api/v1/endpoints/video_catalog.py`:
    *   Import `VideoUpdateRequest` from `app/models/video`.
    *   Import `get_video_for_owner_or_moderator_access` from `app.api.v1.dependencies`.
    *   Implement `PUT /{video_id_path}` endpoint:
        *   Decorator: `@router.put("/{video_id_path}", response_model=VideoDetailResponse, summary="Update video details")`.
        *   Signature: `async def update_video(update_request_data: VideoUpdateRequest, video_to_update: Annotated[Video, Depends(get_video_for_owner_or_moderator_access)])`. The `video_id_path` from the path will be implicitly used by the dependency if named consistently or explicitly mapped. FastAPI handles this if the dependency's path param name matches the route's. For clarity, the dependency `get_video_for_owner_or_moderator_access` already expects `video_id_path`.
        *   Call `updated_video = await video_service.update_video_details(video_to_update=video_to_update, update_request=update_request_data)`.
        *   Return `updated_video`.
4.  In `tests/api/v1/test_dependencies.py`:
    *   Write unit tests for `get_video_for_owner_or_moderator_access`.
    *   Mock `video_service.get_video_by_id`.
    *   Test scenarios: owner access, moderator access, non-owner/non-moderator access (403), video not found (404).
5.  In `tests/services/test_video_service.py`:
    *   Write unit tests for `update_video_details`.
    *   Mock `AstraDBCollection.update_one`.
    *   Test successful update. Verify `update_one` payload and returned `Video` object.
    *   Test with empty `update_request`.
6.  In `tests/api/v1/endpoints/test_video_catalog.py`:
    *   Add tests for `PUT /api/v1/videos/{video_id}`:
        *   Mock `video_service.get_video_by_id` (for the dependency) and `video_service.update_video_details`.
        *   Provide JWTs for owner, moderator, and other users.
        *   Test successful update by owner.
        *   Test successful update by moderator.
        *   Test update attempt by non-owner/non-moderator (expect 403 from dependency).
        *   Test update attempt on non-existent video (expect 404 from dependency).
        *   Test request body validation for `VideoUpdateRequest`.

Current Files to Work On:
*   `app/api/v1/dependencies.py`
*   `app/services/video_service.py`
*   `app/api/v1/endpoints/video_catalog.py`
*   `tests/api/v1/test_dependencies.py`
*   `tests/services/test_video_service.py`
*   `tests/api/v1/endpoints/test_video_catalog.py`

Provide the complete content for each new/modified file.
```---
**Prompt 13 (was 2.5): Record Video View & List Endpoints**
```text
Objective: Implement endpoints to record video views and list videos (latest, by tag, by uploader) with pagination.

Specifications:
1.  Modify `app/core/config.py`:
    *   Add to `Settings` class: `DEFAULT_PAGE_SIZE: int = 10`, `MAX_PAGE_SIZE: int = 100`.
    *   Update `.env.example`.
2.  Modify `app/api/v1/dependencies.py`:
    *   Import `Query` from `fastapi`, `settings` from `app.core.config`.
    *   Define `class PaginationParams`:
        *   `__init__(self, page: int = Query(1, ge=1, description="Page number"), pageSize: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"))`.
        *   Store `self.page` and `self.pageSize`.
    *   Define `common_pagination_params = Annotated[PaginationParams, Depends()]`.
3.  Modify `app/services/video_service.py`:
    *   Import `Tuple` from `typing`.
    *   Import `VideoSummary` from `app/models/video`.
    *   Implement `async def record_video_view(video_id: VideoID, db_table: Optional[AstraDBCollection] = None) -> bool`:
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   Atomically increment `viewCount`. If `astrapy` Data API doesn't support `$inc` directly for `update_one`, this will be a find, modify in Python, then save:
            *   `video_doc = await db_table.find_one(filter={"videoId": str(video_id)})`. If not found, return `False`.
            *   `current_views = video_doc.get("viewCount", 0)`.
            *   `result = await db_table.update_one(filter={"videoId": str(video_id)}, update={"$set": {"viewCount": current_views + 1}})`.
            *   Return `result.modified_count > 0` (or similar check based on `astrapy`'s `UpdateResult`).
    *   Implement `async def list_videos_with_query(query_filter: Dict[str, Any], page: int, page_size: int, sort_options: Optional[Dict[str, Any]] = None, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
        *   This is a helper/generic function for listing.
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   Default `sort_options` to `{"submittedAt": -1}` (descending) if None.
        *   Calculate `skip = (page - 1) * page_size`.
        *   Fetch videos: `cursor = db_table.find(filter=query_filter, skip=skip, limit=page_size, sort=sort_options)`.
        *   Convert cursor to list: `videos_docs = await cursor.to_list(length=page_size)`.
        *   Fetch total count for pagination: `total_items = await db_table.count_documents(filter=query_filter)`.
        *   Map `videos_docs` to `List[VideoSummary]`. Convert `videoId` and `userId` from str to UUID if needed.
        *   Return `(summaries, total_items)`.
    *   Implement `async def list_latest_videos(page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
        *   `query_filter = {"status": VideoStatusEnum.READY}`.
        *   Call `list_videos_with_query(query_filter, page, page_size, db_table=db_table)`.
    *   Implement `async def list_videos_by_tag(tag: str, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
        *   `query_filter = {"status": VideoStatusEnum.READY, "tags": {"$in": [tag]}}`. (Using MongoDB-like syntax for array contains; verify `astrapy` equivalent for Data API, it might be just `{"tags": tag}` if it searches arrays, or specific array operators).
        *   Call `list_videos_with_query(query_filter, page, page_size, db_table=db_table)`.
    *   Implement `async def list_videos_by_user(user_id: UUID, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
        *   `query_filter = {"userId": str(user_id), "status": VideoStatusEnum.READY}` (Only show READY videos of other users).
        *   Call `list_videos_with_query(query_filter, page, page_size, db_table=db_table)`.
4.  Modify `app/api/v1/endpoints/video_catalog.py`:
    *   Import `Response` from `fastapi`.
    *   Import `VideoSummary` from `app/models/video`.
    *   Import `PaginatedResponse, Pagination` from `app/models/common`.
    *   Import `PaginationParams, common_pagination_params` from `app/api/v1.dependencies`.
    *   Implement `POST /{video_id_path}/view`:
        *   Decorator: `@router.post("/{video_id_path}/view", status_code=status.HTTP_204_NO_CONTENT, summary="Record playback view")`. Public.
        *   Signature: `async def record_view(video_id_path: VideoID)`.
        *   Call `video = await video_service.get_video_by_id(video_id=video_id_path)`.
        *   If not `video` or `video.status != VideoStatusEnum.READY`, raise `HTTPException(status.HTTP_404_NOT_FOUND, "Video not found or not available")`.
        *   `success = await video_service.record_video_view(video_id=video_id_path)`. If not `success`, you might log an error but still return 204 as view attempt was made.
        *   Return `Response(status_code=status.HTTP_204_NO_CONTENT)`.
    *   Implement `GET /latest`:
        *   Decorator: `@router.get("/latest", response_model=PaginatedResponse[VideoSummary], summary="Latest videos")`. Public.
        *   Signature: `async def get_latest_videos(pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
        *   Call `summaries, total_items = await video_service.list_latest_videos(page=pagination.page, page_size=pagination.pageSize)`.
        *   `total_pages = (total_items + pagination.pageSize - 1) // pagination.pageSize`.
        *   Return `PaginatedResponse(data=summaries, pagination=Pagination(currentPage=pagination.page, pageSize=pagination.pageSize, totalItems=total_items, totalPages=total_pages))`.
    *   Implement `GET /by-tag/{tag_name}`:
        *   Decorator: `@router.get("/by-tag/{tag_name}", response_model=PaginatedResponse[VideoSummary], summary="Videos by tag")`. (Path param `tag_name` to avoid conflict). Public.
        *   Signature: `async def get_videos_by_tag(tag_name: str, pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
        *   Call `summaries, total_items = await video_service.list_videos_by_tag(tag=tag_name, page=pagination.page, page_size=pagination.pageSize)`.
        *   Construct and return `PaginatedResponse` as above.
5.  Modify `app/api/v1/endpoints/account_management.py` (as per OpenAPI spec `/users/{userId}/videos`):
    *   Import `VideoSummary` from `app/models/video`, `PaginatedResponse, Pagination` from `app/models/common`.
    *   Import `PaginationParams, common_pagination_params` from `app/api/v1.dependencies`.
    *   Import `video_service` from `app.services`. (Ensure circular import is not an issue, or move video listing by user to `video_catalog.py` under a path like `/videos/by-uploader/{user_id}`).
    *   Let's keep it in `video_catalog.py` for service cohesion, and adjust the path to be under `/videos` as suggested in planning.
    *   In `app/api/v1/endpoints/video_catalog.py`, implement `GET /by-uploader/{uploader_id_path}`:
        *   Decorator: `@router.get("/by-uploader/{uploader_id_path}", response_model=PaginatedResponse[VideoSummary], summary="Videos by uploader")`. (Path param `uploader_id_path`). Public.
        *   Signature: `async def get_videos_by_uploader(uploader_id_path: UUID, pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
        *   Call `summaries, total_items = await video_service.list_videos_by_user(user_id=uploader_id_path, page=pagination.page, page_size=pagination.pageSize)`.
        *   Construct and return `PaginatedResponse`.
6.  In `tests/services/test_video_service.py`:
    *   Unit test `record_video_view` (mock DB, check update call).
    *   Unit test `list_videos_with_query` (mock DB find and count_documents, check query formation, pagination, sort).
    *   Unit test `list_latest_videos`, `list_videos_by_tag`, `list_videos_by_user` (these will primarily test the query_filter passed to `list_videos_with_query`).
7.  In `tests/api/v1/endpoints/test_video_catalog.py`:
    *   Test `POST /api/v1/videos/{video_id}/view`.
    *   Test `GET /api/v1/videos/latest` (with/without pagination, empty results).
    *   Test `GET /api/v1/videos/by-tag/{tag}`.
    *   Test `GET /api/v1/videos/by-uploader/{user_id}`.

Current Files to Work On:
*   `app/core/config.py`
*   `.env.example`
*   `app/api/v1/dependencies.py`
*   `app/services/video_service.py`
*   `app/api/v1/endpoints/video_catalog.py`
*   `app/api/v1/endpoints/account_management.py` (if chosen for `/users/{userId}/videos`, otherwise only video_catalog.py)
*   `tests/services/test_video_service.py`
*   `tests/api/v1/endpoints/test_video_catalog.py`

Provide the complete content for each new/modified file. For `astrapy` queries like array contains (`tags: {"$in": [tag]}`) or atomic increments, if the exact Data API syntax via `astrapy` is different from MongoDB, use the correct `astrapy` method or a find-then-update workaround. Assume for `$inc` a read-modify-write is needed. For `$in` with tags, assume `{"tags": {"$contains": tag}}` or similar if `astrapy` has a direct equivalent for searching within an array for an element. If not, this might need a more complex query or schema design. For now, proceed with `{"tags": {"$in": [tag]}}` and note it for `astrapy` specifics.
```