All right, we've covered Search. Now, let's move to **Epic 4: Comments & Ratings** from Phase 1. This epic will allow users to interact with videos by adding comments and ratings.

---

**Phase 1: Epic 4 - Comments & Ratings**
*Goal: Implement functionalities for authenticated users to post comments on videos, view comments for a video or by a user, and rate videos. Public users can view comments and aggregate ratings.*

  *   **Chunk 4.1: Comment Models & Add Comment Endpoint**
      *   **Step 4.1.1:** Create `app/models/comment.py`:
          *   Import `BaseModel, Field` from `pydantic`, `Optional, List` from `typing`, `UUID, uuid4` from `uuid`, `datetime` from `datetime`.
          *   Import `VideoID, UserID` from appropriate model files (e.g., `app.models.video`, `app.models.user`, or define them in `app.models.common` if preferred for wide use). Let's assume `VideoID` is from `app.models.video` and `UserID` from `app.models.user`.
          *   Define `CommentID = UUID`.
          *   Define `class CommentBase(BaseModel)`: `text: str = Field(..., min_length=1, max_length=1000)`.
          *   Define `class CommentCreateRequest(CommentBase)`: (No additional fields beyond `text` for creation by user).
          *   Define `class Comment(CommentBase)`: `commentId: CommentID`, `videoId: VideoID`, `userId: UserID`, `createdAt: datetime`, `updatedAt: datetime`. (API Spec FR-CM-004 mentions "sentiment badge determined when posting" - this implies a `sentiment: Optional[str]` field, e.g. "positive", "neutral", "negative". Add `sentiment: Optional[str] = None`).
          *   Define `class CommentResponse(Comment)`: (Can be an alias or inherit directly).
      *   **Step 4.1.2:** Create `app/services/comment_service.py`:
          *   Import `Optional, List, Dict, Any, Tuple` from `typing`, `UUID, uuid4` from `uuid`, `datetime, timezone` from `datetime`.
          *   Import `get_table` from `app/db/astra_client`, `AstraDBCollection` from `astrapy.db`.
          *   Import `CommentCreateRequest, Comment, CommentID` from `app.models.comment`.
          *   Import `VideoID, UserID` type aliases.
          *   Import `User` from `app.models.user`.
          *   Import `video_service` to check video existence.
          *   Define `COMMENTS_TABLE_NAME: str = "comments"`.
          *   Implement `async def _determine_sentiment(text: str) -> Optional[str]`:
              *   Placeholder for sentiment analysis. For now, `return None` or a random choice like `random.choice(["positive", "neutral", "negative", None])`. Import `random`.
          *   Implement `async def add_comment_to_video(video_id: VideoID, request: CommentCreateRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Comment`:
              *   Check if video exists: `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video` or `target_video.status != VideoStatusEnum.READY`, raise `HTTPException 404 ("Video not found or not available for comments")`.
              *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
              *   Determine sentiment: `comment_sentiment = await _determine_sentiment(request.text)`.
              *   Construct `Comment` Pydantic model: `commentId=uuid4()`, `videoId=video_id`, `userId=current_user.userId`, `text=request.text`, `createdAt=datetime.now(timezone.utc)`, `updatedAt=datetime.now(timezone.utc)`, `sentiment=comment_sentiment`.
              *   Convert to dict, ensuring UUIDs are strings for DB: `comment_doc = new_comment.model_dump()`. (e.g. `comment_doc["commentId"] = str(new_comment.commentId)`).
              *   `await db_table.insert_one(document=comment_doc)`.
              *   Return the created `Comment` Pydantic model.
      *   **Step 4.1.3:** Create `app/api/v1/endpoints/comments_ratings.py`:
          *   Import `APIRouter, Depends, HTTPException, status` from `fastapi`.
          *   Import `CommentCreateRequest, CommentResponse` (aliased as `Comment`) from `app/models.comment`.
          *   Import `VideoID` from `app/models.video`.
          *   Import `User` from `app/models.user`.
          *   Import `get_current_viewer` from `app.api.v1.dependencies` (posting comments requires "viewer" privileges).
          *   Import `comment_service` from `app.services`.
          *   Import `Annotated` from `typing`.
          *   Initialize `router = APIRouter(tags=["Comments & Ratings"])`.
          *   Implement `POST /videos/{videoId}/comments` endpoint:
              *   Path operation: `@router.post("/videos/{video_id_path}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, summary="Add comment")`.
              *   Signature: `async def post_comment(video_id_path: VideoID, comment_data: CommentCreateRequest, current_user: Annotated[User, Depends(get_current_viewer)])`.
              *   Call `new_comment = await comment_service.add_comment_to_video(video_id=video_id_path, request=comment_data, current_user=current_user)`.
              *   Return `new_comment`.
      *   **Step 4.1.4:** Modify `app/main.py` (or monolith entrypoint): Include `comments_ratings.router`.
      *   **Step 4.1.5:** Tests:
          *   Create `tests/models/test_comment.py` if any model-specific logic/validation needs testing (likely not for these simple models).
          *   Create `tests/services/test_comment_service.py`:
              *   Unit test `_determine_sentiment` (simple for now).
              *   Unit test `add_comment_to_video`. Mock `video_service.get_video_by_id`, `_determine_sentiment`, and DB calls. Test successful comment, video not found/not ready.
          *   Create `tests/api/v1/endpoints/test_comments_ratings.py`:
              *   Integration test `POST /videos/{videoId}/comments`. Mock `comment_service.add_comment_to_video`. Test with "viewer" token, no token (401), video not found (service raises 404). Test request body validation.

  *   **Chunk 4.2: List Comments Endpoints (For Video, By User)**
      *   **Step 4.2.1:** Modify `app/services/comment_service.py`:
          *   Import `VideoID, UserID, CommentID, Comment` (already there).
          *   Implement `async def list_comments_for_video(video_id: VideoID, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[Comment], int]`:
              *   Check if video exists: `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video`, return `([], 0)` or raise 404 early if preferred (API implies list is public).
              *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
              *   Query `COMMENTS_TABLE_NAME` for comments where `videoId == str(video_id)`.
              *   Sort by `createdAt` descending (or ascending as per spec/preference).
              *   Implement pagination (skip, limit). Fetch total count for the `videoId`.
              *   Map results to `List[Comment]`. Convert UUIDs.
              *   Return `(comments_list, total_items)`.
          *   Implement `async def list_comments_by_user(user_id: UserID, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[Comment], int]`:
              *   (Optional: Check if user exists via `user_service` if strictness needed, or just query comments).
              *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
              *   Query for comments where `userId == str(user_id)`.
              *   Sort by `createdAt` descending. Implement pagination. Fetch total count for `userId`.
              *   Map to `List[Comment]`.
              *   Return `(comments_list, total_items)`.
      *   **Step 4.2.2:** Modify `app/api/v1/endpoints/comments_ratings.py`:
          *   Import `List` from `typing`.
          *   Import `PaginatedResponse, Pagination` from `app.models.common`.
          *   Import `PaginationParams, common_pagination_params` from `app.api.v1.dependencies`.
          *   Import `UserID` from `app.models.user`.
          *   Implement `GET /videos/{videoId}/comments` endpoint:
              *   Path operation: `@router.get("/videos/{video_id_path}/comments", response_model=PaginatedResponse[CommentResponse], summary="List comments for a video")`. Public.
              *   Signature: `async def get_comments_for_video(video_id_path: VideoID, pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
              *   Call `comments, total = await comment_service.list_comments_for_video(...)`.
              *   Construct and return `PaginatedResponse`.
          *   Implement `GET /users/{userId}/comments` endpoint:
              *   Path operation: `@router.get("/users/{user_id_path}/comments", response_model=PaginatedResponse[CommentResponse], summary="List comments by user")`. Public.
              *   Signature: `async def get_comments_by_user(user_id_path: UserID, pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
              *   Call `comments, total = await comment_service.list_comments_by_user(...)`.
              *   Construct and return `PaginatedResponse`.
      *   **Step 4.2.3:** Tests:
          *   In `tests/services/test_comment_service.py`: Unit test `list_comments_for_video` and `list_comments_by_user`. Mock DB calls. Test pagination, sorting, empty results.
          *   In `tests/api/v1/endpoints/test_comments_ratings.py`: Integration test the two new GET endpoints. Mock service calls. Test pagination parameters.

  *   **Chunk 4.3: Rating Models & Rate Video Endpoint**
      *   **Step 4.3.1:** Create `app/models/rating.py`:
          *   Import `BaseModel, Field` from `pydantic`, `Optional` from `typing`, `UUID` from `uuid`, `datetime` from `datetime`.
          *   Import `VideoID, UserID` type aliases.
          *   Define `RatingValue = int` (or use `Field(ge=1, le=5)` directly).
          *   Define `class RatingBase(BaseModel)`: `rating: RatingValue = Field(..., ge=1, le=5)`.
          *   Define `class RatingCreateOrUpdateRequest(RatingBase)`: (Same as base).
          *   Define `class Rating(RatingBase)`: `videoId: VideoID`, `userId: UserID`, `createdAt: datetime`, `updatedAt: datetime`.
          *   Define `class RatingResponse(Rating)`: (Can be alias/inherit).
          *   Define `class AggregateRatingResponse(BaseModel)`: `videoId: VideoID`, `averageRating: Optional[float] = None`, `totalRatings: int = 0`, `currentUserRating: Optional[RatingValue] = None` (if viewer is authenticated).
      *   **Step 4.3.2:** Create `app/services/rating_service.py`:
          *   Import `Optional, Tuple` from `typing`, `UUID` from `uuid`, `datetime, timezone` from `datetime`, `List` from `typing`.
          *   Import `get_table` from `app/db/astra_client`, `AstraDBCollection` from `astrapy.db`.
          *   Import `RatingCreateOrUpdateRequest, Rating, RatingValue` from `app.models.rating`.
          *   Import `VideoID, UserID` type aliases.
          *   Import `User` from `app.models.user`.
          *   Import `video_service`.
          *   Define `RATINGS_TABLE_NAME: str = "ratings"`.
          *   Implement `async def _update_video_aggregate_rating(video_id: VideoID, ratings_db_table: AstraDBCollection, videos_db_table: AstraDBCollection)`:
              *   Fetches all ratings for `video_id` from `ratings_db_table`.
              *   Calculates `average_rating` and `total_ratings`.
              *   Updates the corresponding video document in `VIDEOS_TABLE_NAME` (via `videos_db_table`) with these new aggregate values.
          *   Implement `async def rate_video(video_id: VideoID, request: RatingCreateOrUpdateRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Rating`:
              *   Check if video exists: `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video` or `target_video.status != VideoStatusEnum.READY`, raise `HTTPException 404 ("Video not found or not available for rating")`.
              *   If `db_table` is None, `db_table = await get_table(RATINGS_TABLE_NAME)`.
              *   Check for existing rating by this user for this video: `existing_rating_doc = await db_table.find_one(filter={"videoId": str(video_id), "userId": str(current_user.userId)})`.
              *   If `existing_rating_doc`: Update it with new `rating` and `updatedAt`.
              *   Else: Create new rating document: `videoId`, `userId`, `rating`, `createdAt`, `updatedAt`. Insert it.
              *   After insert/update, call `await _update_video_aggregate_rating(video_id, db_table, await get_table(video_service.VIDEOS_TABLE_NAME))`.
              *   Return the created/updated `Rating` Pydantic model.
      *   **Step 4.3.3:** Modify `app/api/v1/endpoints/comments_ratings.py`:
          *   Import `RatingCreateOrUpdateRequest, RatingResponse, AggregateRatingResponse` from `app.models.rating`.
          *   Import `rating_service` from `app.services`.
          *   Implement `POST /videos/{videoId}/ratings` endpoint:
              *   Path operation: `@router.post("/videos/{video_id_path}/ratings", response_model=RatingResponse, summary="Rate video (1-5) - creates or updates")`.
              *   Signature: `async def post_rating(video_id_path: VideoID, rating_data: RatingCreateOrUpdateRequest, current_user: Annotated[User, Depends(get_current_viewer)])`.
              *   Call `new_or_updated_rating = await rating_service.rate_video(...)`.
              *   Return `new_or_updated_rating`.
      *   **Step 4.3.4:** Tests:
          *   Create `tests/models/test_rating.py` for `RatingValue` validation if using `conint` or complex `Field`.
          *   Create `tests/services/test_rating_service.py`: Unit test `_update_video_aggregate_rating` and `rate_video`. Mock DB and `video_service` calls. Test new rating, updating rating, aggregate calculation.
          *   In `tests/api/v1/endpoints/test_comments_ratings.py`: Integration test `POST /videos/{videoId}/ratings`. Mock `rating_service`. Test with "viewer" token, rating creation, rating update. Test request body validation (1-5).

  *   **Chunk 4.4: Get Ratings Endpoint**
      *   **Step 4.4.1:** Modify `app/services/rating_service.py`:
          *   Implement `async def get_video_ratings(video_id: VideoID, current_user_id: Optional[UserID] = None, ratings_db_table: Optional[AstraDBCollection] = None, videos_db_table: Optional[AstraDBCollection] = None) -> AggregateRatingResponse`:
              *   Check if video exists: `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video`, raise `HTTPException 404`.
              *   Fetch `averageRating` and `totalRatings` directly from the `target_video` object (these are now pre-aggregated on the video document by `_update_video_aggregate_rating`).
              *   Initialize `user_rating_value: Optional[RatingValue] = None`.
              *   If `current_user_id`:
                  *   If `ratings_db_table` is None, `ratings_db_table = await get_table(RATINGS_TABLE_NAME)`.
                  *   Fetch the user's specific rating: `user_rating_doc = await ratings_db_table.find_one(filter={"videoId": str(video_id), "userId": str(current_user_id)})`.
                  *   If `user_rating_doc`, `user_rating_value = user_rating_doc["rating"]`.
              *   Return `AggregateRatingResponse(videoId=video_id, averageRating=target_video.averageRating, totalRatings=int(target_video.viewCount * (target_video.averageRating or 0)) if target_video.averageRating else 0, currentUserRating=user_rating_value)`. Note: `totalRatings` based on viewCount*avgRating is not right. It should be the count of rating entries. We need a `totalRatingsCount` field on the Video model, updated by `_update_video_aggregate_rating`.
              *   Correction for `_update_video_aggregate_rating` and `get_video_ratings`:
                  *   `_update_video_aggregate_rating` should calculate `total_ratings_count` (count of rating documents for the video) and update this on the `Video` document along with `averageRating`.
                  *   `get_video_ratings` should fetch `total_ratings_count` from the `Video` document.
                  *   Update `Video` model in `app/models/video.py` to include `totalRatingsCount: int = 0`.
      *   **Step 4.4.2:** Modify `app/api/v1/endpoints/comments_ratings.py`:
          *   Import `get_current_user_from_token` for optional authentication.
          *   Import `Optional` from `typing`.
          *   Implement `GET /videos/{videoId}/ratings` endpoint:
              *   Path operation: `@router.get("/videos/{video_id_path}/ratings", response_model=AggregateRatingResponse, summary="Get aggregate + (viewer’s) rating")`.
              *   Signature: `async def get_ratings_for_video(video_id_path: VideoID, current_user: Annotated[Optional[User], Depends(get_current_user_from_token)] = None)`. (Dependency is optional).
              *   `user_id_for_query = current_user.userId if current_user else None`.
              *   Call `agg_rating_data = await rating_service.get_video_ratings(video_id=video_id_path, current_user_id=user_id_for_query)`.
              *   Return `agg_rating_data`.
      *   **Step 4.4.3:** Tests:
          *   In `tests/services/test_rating_service.py`: Unit test `get_video_ratings` (and the corrected `_update_video_aggregate_rating`). Test with/without authenticated user, video not found.
          *   In `tests/api/v1/endpoints/test_comments_ratings.py`: Integration test `GET /videos/{videoId}/ratings`. Mock service. Test with and without authentication token to check `currentUserRating`.

---

This completes the plan for Epic 4. I'll now generate the LLM prompts.

## LLM Prompts - Iteration 4 (Epic 4: Comments & Ratings)

---
**Prompt 16 (was 4.1): Comment Models & Add Comment Endpoint**
```text
Objective: Define Pydantic models for Comments and implement an endpoint for authenticated users ("viewer" role and above) to add comments to videos.

Specifications:
1.  Create `app/models/comment.py`:
    *   Import `BaseModel, Field` from `pydantic`, `Optional, List` from `typing`, `UUID, uuid4` from `uuid`, `datetime` from `datetime`.
    *   Attempt to import `VideoID` from `app.models.video` and `UserID` from `app.models.user`. If this causes circular dependency issues at this stage, define them as `UserID = UUID` and `VideoID = UUID` directly in `comment.py` for now and make a note to centralize type aliases like `UserID`, `VideoID` into `app.models.common` later.
    *   Define `CommentID = UUID`.
    *   Define `class CommentBase(BaseModel)`: `text: str = Field(..., min_length=1, max_length=1000)`.
    *   Define `class CommentCreateRequest(CommentBase)`: (No additional fields).
    *   Define `class Comment(CommentBase)`: `commentId: CommentID`, `videoId: VideoID`, `userId: UserID`, `createdAt: datetime`, `updatedAt: datetime`, `sentiment: Optional[str] = None`.
    *   Define `class CommentResponse(Comment)`: (Can use `pass` if identical to `Comment`).
2.  Create `app/services/comment_service.py`:
    *   Import `Optional, List, Dict, Any, Tuple, random` from `typing` and `random`.
    *   Import `UUID, uuid4` from `uuid`, `datetime, timezone` from `datetime`.
    *   Import `get_table` from `app.db.astra_client`, `AstraDBCollection` from `astrapy.db`.
    *   Import `CommentCreateRequest, Comment, CommentID` from `app.models.comment`.
    *   Import `VideoID, UserID` (from wherever they are defined).
    *   Import `User` from `app.models.user`.
    *   Import `video_service` from `app.services`.
    *   Import `VideoStatusEnum` from `app.models.video`.
    *   Import `HTTPException, status` from `fastapi`.
    *   Define `COMMENTS_TABLE_NAME: str = "comments"`.
    *   Implement `async def _determine_sentiment(text: str) -> Optional[str]`:
        *   `# TODO: Integrate a real sentiment analysis tool.`
        *   `return random.choice(["positive", "neutral", "negative", None]) # Placeholder`
    *   Implement `async def add_comment_to_video(video_id: VideoID, request: CommentCreateRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Comment`:
        *   Call `target_video = await video_service.get_video_by_id(video_id)`.
        *   If not `target_video` or `target_video.status != VideoStatusEnum.READY`: raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found or not available for comments")`.
        *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
        *   `comment_sentiment = await _determine_sentiment(request.text)`.
        *   `now = datetime.now(timezone.utc)`.
        *   `new_comment_obj = Comment(commentId=uuid4(), videoId=video_id, userId=current_user.userId, text=request.text, createdAt=now, updatedAt=now, sentiment=comment_sentiment)`.
        *   Prepare document for DB: `comment_doc_to_insert = new_comment_obj.model_dump()`. Convert UUID fields (`commentId`, `videoId`, `userId`) to `str()` before insertion.
        *   `await db_table.insert_one(document=comment_doc_to_insert)`.
        *   Return `new_comment_obj`.
3.  Create `app/api/v1/endpoints/comments_ratings.py`:
    *   Import `APIRouter, Depends, HTTPException, status` from `fastapi`.
    *   Import `CommentCreateRequest, CommentResponse` from `app.models.comment`.
    *   Import `VideoID` from `app.models.video`.
    *   Import `User` from `app.models.user`.
    *   Import `get_current_viewer` from `app.api.v1.dependencies`.
    *   Import `comment_service` from `app.services`.
    *   Import `Annotated` from `typing`.
    *   Initialize `router = APIRouter(tags=["Comments & Ratings"])`.
    *   Implement `POST /videos/{video_id_path}/comments` endpoint:
        *   Decorator: `@router.post("/videos/{video_id_path}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, summary="Add comment to video")`.
        *   Signature: `async def post_comment_to_video(video_id_path: VideoID, comment_data: CommentCreateRequest, current_user: Annotated[User, Depends(get_current_viewer)])`.
        *   Call `new_comment = await comment_service.add_comment_to_video(video_id=video_id_path, request=comment_data, current_user=current_user)`.
        *   Return `new_comment`.
4.  Modify `app/main.py` (or monolith entrypoint):
    *   Import `comments_ratings_router` (rename `router` in `comments_ratings.py`).
    *   Include it in `api_router_v1`: `api_router_v1.include_router(comments_ratings.router)`.
5.  Create `tests/services/test_comment_service.py`:
    *   Import `pytest`, `unittest.mock.AsyncMock`, `unittest.mock.patch`.
    *   Import relevant service functions, models, and `VideoStatusEnum`.
    *   Test `_determine_sentiment`.
    *   Test `add_comment_to_video`:
        *   Mock `video_service.get_video_by_id` to return a valid video / unavailable video / None.
        *   Mock `_determine_sentiment`.
        *   Mock `get_table` and `AstraDBCollection.insert_one`.
        *   Test successful comment creation. Verify data passed to `insert_one` (UUIDs as strings).
        *   Test commenting on non-existent or non-ready video.
6.  Create `tests/api/v1/endpoints/test_comments_ratings.py`:
    *   Import `AsyncClient`, `status`, relevant models.
    *   Write integration tests for `POST /api/v1/videos/{videoId}/comments`:
        *   Mock `comment_service.add_comment_to_video`.
        *   Use helper to get JWT for "viewer".
        *   Test successful comment.
        *   Test commenting without authentication (expect 401).
        *   Test when service indicates video not found (mock service to raise HTTPException 404).
        *   Test request body validation (e.g., empty comment text).

Current Files to Work On:
*   `app/models/comment.py`
*   `app/services/comment_service.py`
*   `app/api/v1/endpoints/comments_ratings.py`
*   `app/main.py`
*   `tests/services/test_comment_service.py`
*   `tests/api/v1/endpoints/test_comments_ratings.py`

Provide the complete content for each new/modified file. Remember to convert UUIDs to strings when preparing documents for AstraDB JSON storage.
```
---
**Prompt 17 (was 4.2): List Comments Endpoints (For Video, By User)**
```text
Objective: Implement public endpoints to list comments for a specific video and all comments made by a specific user, with pagination.

Specifications:
1.  Modify `app/services/comment_service.py`:
    *   Import `Tuple, List` from `typing`.
    *   Import `VideoID, UserID, CommentID, Comment` from `app.models.comment`.
    *   (Ensure `video_service` and `VideoStatusEnum` are imported).
    *   (Ensure `get_table`, `COMMENTS_TABLE_NAME` are available).
    *   Implement `async def list_comments_for_video(video_id: VideoID, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[Comment], int]`:
        *   Call `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video`: raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")`. (API implies public list, but comments are for a video, so video must exist).
        *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
        *   `query_filter = {"videoId": str(video_id)}`.
        *   `sort_options = {"createdAt": -1}` (newest first, or 1 for oldest).
        *   `skip = (page - 1) * page_size`.
        *   `comments_cursor = db_table.find(filter=query_filter, skip=skip, limit=page_size, sort=sort_options)`.
        *   `comments_docs = await comments_cursor.to_list(length=page_size)`.
        *   `total_items = await db_table.count_documents(filter=query_filter)`.
        *   Map `comments_docs` to `List[Comment]`. For each doc, convert `commentId`, `videoId`, `userId` string fields back to `UUID`. Convert `createdAt`, `updatedAt` from string (if stored as ISO string by DB) or timestamp to `datetime`.
        *   Return `(mapped_comments_list, total_items)`.
    *   Implement `async def list_comments_by_user(user_id: UserID, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[Comment], int]`:
        *   (Optional: check if user exists via `user_service.get_user_by_id_from_table` if needed).
        *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
        *   `query_filter = {"userId": str(user_id)}`.
        *   `sort_options = {"createdAt": -1}`.
        *   `skip = (page - 1) * page_size`.
        *   `comments_cursor = db_table.find(filter=query_filter, skip=skip, limit=page_size, sort=sort_options)`.
        *   `comments_docs = await comments_cursor.to_list(length=page_size)`.
        *   `total_items = await db_table.count_documents(filter=query_filter)`.
        *   Map `comments_docs` to `List[Comment]` as above.
        *   Return `(mapped_comments_list, total_items)`.
2.  Modify `app/api/v1/endpoints/comments_ratings.py`:
    *   Import `List` from `typing`. (If not already).
    *   Import `PaginatedResponse, Pagination` from `app/models.common`.
    *   Import `PaginationParams, common_pagination_params` from `app.api.v1.dependencies`.
    *   Import `CommentResponse` (aliased as `Comment` if preferred for response model type) from `app.models.comment`.
    *   Import `UserID` from `app.models.user`.
    *   Implement `GET /videos/{video_id_path}/comments`:
        *   Decorator: `@router.get("/videos/{video_id_path}/comments", response_model=PaginatedResponse[CommentResponse], summary="List comments for a video")`. Public.
        *   Signature: `async def list_video_comments(video_id_path: VideoID, pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
        *   Call `comments_list, total_items = await comment_service.list_comments_for_video(video_id=video_id_path, page=pagination.page, page_size=pagination.pageSize)`.
        *   `total_pages = (total_items + pagination.pageSize - 1) // pagination.pageSize if pagination.pageSize > 0 else 0`.
        *   Return `PaginatedResponse(data=comments_list, pagination=Pagination(currentPage=pagination.page, pageSize=pagination.pageSize, totalItems=total_items, totalPages=total_pages))`.
    *   Implement `GET /users/{user_id_path}/comments`:
        *   Decorator: `@router.get("/users/{user_id_path}/comments", response_model=PaginatedResponse[CommentResponse], summary="List comments by a user")`. Public.
        *   Signature: `async def list_user_comments(user_id_path: UserID, pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
        *   Call `comments_list, total_items = await comment_service.list_comments_by_user(user_id=user_id_path, page=pagination.page, page_size=pagination.pageSize)`.
        *   Construct and return `PaginatedResponse` as above.
3.  In `tests/services/test_comment_service.py`:
    *   Add unit tests for `list_comments_for_video` and `list_comments_by_user`.
    *   Mock `video_service.get_video_by_id` (for `list_comments_for_video`).
    *   Mock `get_table`, `AstraDBCollection.find`, `AstraDBCollection.count_documents`.
    *   Test correct filter construction, pagination (skip, limit), sorting.
    *   Test mapping of DB docs to `Comment` models, including type conversions for UUIDs and datetimes.
    *   Test video not found scenario for `list_comments_for_video`.
4.  In `tests/api/v1/endpoints/test_comments_ratings.py`:
    *   Add integration tests for `GET /api/v1/videos/{videoId}/comments` and `GET /api/v1/users/{userId}/comments`.
    *   Mock the corresponding service calls (`comment_service.list_comments_for_video`, `comment_service.list_comments_by_user`).
    *   Test successful response with data.
    *   Test pagination query parameters are correctly passed and reflected in mock calls.
    *   Test empty list scenario.
    *   Test `video not found` scenario for listing comments for a video.

Current Files to Work On:
*   `app/services/comment_service.py`
*   `app/api/v1/endpoints/comments_ratings.py`
*   `tests/services/test_comment_service.py`
*   `tests/api/v1/endpoints/test_comments_ratings.py`

Provide the complete content for each new/modified file. Ensure correct data type mapping when retrieving documents from AstraDB and converting them to Pydantic models.
```
---
**Prompt 18 (was 4.3): Rating Models & Rate Video Endpoint**
```text
Objective: Define Pydantic models for Ratings and implement an endpoint for authenticated users ("viewer" and above) to rate a video (1-5 stars), which creates or updates their existing rating. This will also involve updating an aggregate rating on the video document.

Specifications:
1.  Create `app/models/rating.py`:
    *   Import `BaseModel, Field` from `pydantic`, `Optional, List` from `typing`, `UUID` from `uuid`, `datetime` from `datetime`.
    *   Attempt to import `VideoID` from `app.models.video` and `UserID` from `app.models.user` (or use local UUID aliases if needed, with a TODO to centralize).
    *   Define `RatingValue = int` (or use `conint` from pydantic if you want to be more explicit, e.g., `pydantic.conint(ge=1, le=5)`).
    *   Define `class RatingBase(BaseModel)`: `rating: RatingValue = Field(..., ge=1, le=5, description="Rating value between 1 and 5")`.
    *   Define `class RatingCreateOrUpdateRequest(RatingBase)`: (No additional fields).
    *   Define `class Rating(RatingBase)`: `videoId: VideoID`, `userId: UserID`, `createdAt: datetime`, `updatedAt: datetime`. (No `ratingId` needed if `(videoId, userId)` is the effective key).
    *   Define `class RatingResponse(Rating)`: (Can use `pass`).
    *   Define `class AggregateRatingResponse(BaseModel)`: `videoId: VideoID`, `averageRating: Optional[float] = None`, `totalRatingsCount: int = 0`, `currentUserRating: Optional[RatingValue] = None`.
2.  Modify `app/models/video.py`:
    *   Add `totalRatingsCount: int = Field(0, ge=0)` to the `Video` model. (Default 0).
3.  Create `app/services/rating_service.py`:
    *   Import `Optional, Tuple, List` from `typing`, `UUID` from `uuid`, `datetime, timezone` from `datetime`.
    *   Import `get_table` from `app/db/astra_client`, `AstraDBCollection` from `astrapy.db`.
    *   Import `RatingCreateOrUpdateRequest, Rating, RatingValue` from `app.models.rating`.
    *   Import `VideoID, UserID` (from common or model files).
    *   Import `User` from `app.models.user`.
    *   Import `video_service` from `app.services`, and `Video, VideoStatusEnum` from `app.models.video`.
    *   Import `HTTPException, status` from `fastapi`.
    *   Define `RATINGS_TABLE_NAME: str = "ratings"`.
    *   Implement `async def _update_video_aggregate_rating(video_id: VideoID, ratings_db_table: AstraDBCollection, videos_db_table: AstraDBCollection)`:
        *   `ratings_cursor = ratings_db_table.find(filter={"videoId": str(video_id)}, projection={"rating": 1})`.
        *   `all_ratings_for_video_docs = await ratings_cursor.to_list(length=None)`.
        *   If `all_ratings_for_video_docs`:
            *   `ratings_values = [doc["rating"] for doc in all_ratings_for_video_docs if "rating" in doc]`.
            *   `total_ratings_count = len(ratings_values)`.
            *   `average_rating = sum(ratings_values) / total_ratings_count if total_ratings_count > 0 else None`.
        *   Else:
            *   `total_ratings_count = 0`.
            *   `average_rating = None`.
        *   `await videos_db_table.update_one(filter={"videoId": str(video_id)}, update={"$set": {"averageRating": average_rating, "totalRatingsCount": total_ratings_count, "updatedAt": datetime.now(timezone.utc)}})`.
    *   Implement `async def rate_video(video_id: VideoID, request: RatingCreateOrUpdateRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Rating`:
        *   Call `target_video = await video_service.get_video_by_id(video_id)`.
        *   If not `target_video` or `target_video.status != VideoStatusEnum.READY`: raise `HTTPException(status.HTTP_404_NOT_FOUND, "Video not found or not available for rating")`.
        *   If `db_table` is None, `db_table = await get_table(RATINGS_TABLE_NAME)`.
        *   `now = datetime.now(timezone.utc)`.
        *   `rating_filter = {"videoId": str(video_id), "userId": str(current_user.userId)}`.
        *   `existing_rating_doc = await db_table.find_one(filter=rating_filter)`.
        *   If `existing_rating_doc`:
            *   `await db_table.update_one(filter=rating_filter, update={"$set": {"rating": request.rating, "updatedAt": now}})`.
            *   `created_at_dt = existing_rating_doc.get("createdAt", now)` (handle if not string or convert from string).
            *   `updated_rating_obj = Rating(videoId=video_id, userId=current_user.userId, rating=request.rating, createdAt=created_at_dt, updatedAt=now)`.
        *   Else:
            *   `new_rating_obj = Rating(videoId=video_id, userId=current_user.userId, rating=request.rating, createdAt=now, updatedAt=now)`.
            *   `rating_doc_to_insert = new_rating_obj.model_dump()`. Convert UUIDs to str.
            *   `await db_table.insert_one(document=rating_doc_to_insert)`.
            *   `updated_rating_obj = new_rating_obj`.
        *   Call `await _update_video_aggregate_rating(video_id, db_table, await get_table(video_service.VIDEOS_TABLE_NAME))`.
        *   Return `updated_rating_obj`.
4.  Modify `app/api/v1/endpoints/comments_ratings.py`:
    *   Import `RatingCreateOrUpdateRequest, RatingResponse` from `app/models.rating`. (AggregateRatingResponse not needed for POST).
    *   Import `rating_service` from `app.services`.
    *   Implement `POST /videos/{video_id_path}/ratings`:
        *   Decorator: `@router.post("/videos/{video_id_path}/ratings", response_model=RatingResponse, summary="Rate a video (1-5 stars)")`.
        *   Signature: `async def submit_video_rating(video_id_path: VideoID, rating_data: RatingCreateOrUpdateRequest, current_user: Annotated[User, Depends(get_current_viewer)])`.
        *   Call `rating_obj = await rating_service.rate_video(video_id=video_id_path, request=rating_data, current_user=current_user)`.
        *   Return `rating_obj`.
5.  Create `tests/services/test_rating_service.py`:
    *   Unit test `_update_video_aggregate_rating`: Mock DB calls. Verify correct calculation and update payload for video document.
    *   Unit test `rate_video`: Mock `video_service.get_video_by_id`, `_update_video_aggregate_rating`, and DB calls for ratings table. Test new rating creation, existing rating update. Video not found/ready.
6.  In `tests/api/v1/endpoints/test_comments_ratings.py`:
    *   Add integration tests for `POST /api/v1/videos/{videoId}/ratings`.
    *   Mock `rating_service.rate_video`.
    *   Test with "viewer" token.
    *   Test rating creation and update scenarios (service mock returns different `createdAt` vs `updatedAt`).
    *   Test request body validation (rating value 1-5).
    *   Test video not found (service raises 404).

Current Files to Work On:
*   `app/models/rating.py`
*   `app/models/video.py` (add `totalRatingsCount`)
*   `app/services/rating_service.py`
*   `app/api/v1/endpoints/comments_ratings.py`
*   `tests/services/test_rating_service.py`
*   `tests/api/v1/endpoints/test_comments_ratings.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 19 (was 4.4): Get Ratings Endpoint**
```text
Objective: Implement a public endpoint to retrieve the aggregate rating for a video, and optionally the current user's rating if authenticated.

Specifications:
1.  Modify `app/services/rating_service.py`:
    *   Import `AggregateRatingResponse, RatingValue` from `app/models.rating`.
    *   Import `UserID` (if not already).
    *   Implement `async def get_video_ratings_summary(video_id: VideoID, current_user_id: Optional[UserID] = None, ratings_db_table: Optional[AstraDBCollection] = None, videos_db_table: Optional[AstraDBCollection] = None) -> AggregateRatingResponse`:
        *   (Rename from `get_video_ratings` to avoid conflict if a more detailed list of all ratings was ever needed).
        *   If `videos_db_table` is None, `videos_db_table = await get_table(video_service.VIDEOS_TABLE_NAME)`.
        *   Call `target_video_doc = await videos_db_table.find_one(filter={"videoId": str(video_id)})`.
        *   If not `target_video_doc`: raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")`.
        *   `avg_rating = target_video_doc.get("averageRating")`.
        *   `total_count = target_video_doc.get("totalRatingsCount", 0)`.
        *   `user_personal_rating: Optional[RatingValue] = None`.
        *   If `current_user_id`:
            *   If `ratings_db_table` is None, `ratings_db_table = await get_table(RATINGS_TABLE_NAME)`.
            *   `user_rating_doc = await ratings_db_table.find_one(filter={"videoId": str(video_id), "userId": str(current_user_id)})`.
            *   If `user_rating_doc` and "rating" in `user_rating_doc`: `user_personal_rating = user_rating_doc["rating"]`.
        *   Return `AggregateRatingResponse(videoId=video_id, averageRating=avg_rating, totalRatingsCount=total_count, currentUserRating=user_personal_rating)`.
2.  Modify `app/api/v1/endpoints/comments_ratings.py`:
    *   Import `AggregateRatingResponse` from `app/models.rating`.
    *   Import `get_current_user_from_token` from `app.api.v1.dependencies` (used for *optional* auth).
    *   Import `Optional` from `typing`.
    *   Implement `GET /videos/{video_id_path}/ratings`:
        *   Decorator: `@router.get("/videos/{video_id_path}/ratings", response_model=AggregateRatingResponse, summary="Get aggregate rating and current user's rating if authenticated")`.
        *   Signature: `async def get_video_ratings_info(video_id_path: VideoID, current_user_optional: Annotated[Optional[User], Depends(get_current_user_from_token)] = None)`.
            *   Note: `get_current_user_from_token` will raise 401 if token invalid. To make it truly optional (i.e., proceed if no token or invalid token), the dependency itself needs to be modified to not raise on error but return `None`.
            *   Let's adjust `get_current_user_from_token` in `dependencies.py` for this:
                *   Modify `reusable_oauth2` to have `auto_error=False`.
                *   In `get_current_user_token_payload`, if `token is None`, return `None` early. If decoding fails, also return `None` instead of raising HTTPException.
                *   In `get_current_user_from_token`, if `payload is None` (from `get_current_user_token_payload` returning `None`), then return `None`.
        *   `user_id_for_query = current_user_optional.userId if current_user_optional else None`.
        *   Call `agg_rating_data = await rating_service.get_video_ratings_summary(video_id=video_id_path, current_user_id=user_id_for_query)`.
        *   Return `agg_rating_data`.
3.  Modify `app/api/v1/dependencies.py` (to make `get_current_user_from_token` truly optional):
    *   Change `reusable_oauth2 = OAuth2PasswordBearer(...)` to `reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/users/login", auto_error=False)`.
    *   In `get_current_user_token_payload(token: Annotated[Optional[str], Depends(reusable_oauth2)])`:
        *   If `token is None`, return `None`.
        *   In the `try-except` block for JWT decoding, if any `JWTError` or `ValidationError` occurs, or token is expired, log the error and return `None` instead of raising `HTTPException`.
    *   In `get_current_user_from_token(payload: Annotated[Optional[TokenPayload], Depends(get_current_user_token_payload)])`:
        *   If `payload is None`, return `None`.
        *   If `payload.sub` is None, return `None`. (Or log and return None).
        *   When calling `user_service.get_user_by_id_from_table`, if it returns `None`, then this dependency should return `None`.
    *   This makes `Depends(get_current_user_from_token)` suitable for optional authentication.
4.  In `tests/services/test_rating_service.py`:
    *   Add unit tests for `get_video_ratings_summary`.
    *   Mock DB calls for both ratings and videos tables.
    *   Test scenarios:
        *   Video found, no user provided (currentUserRating is None).
        *   Video found, user provided, user has a rating.
        *   Video found, user provided, user has no rating.
        *   Video not found (service raises HTTPException).
        *   Video has no ratings yet (avg is None, total is 0).
5.  In `tests/api/v1/test_dependencies.py`:
    *   Update tests for `get_current_user_token_payload` and `get_current_user_from_token` to reflect their new optional behavior (returning `None` on error/no token instead of raising).
6.  In `tests/api/v1/endpoints/test_comments_ratings.py`:
    *   Add integration tests for `GET /api/v1/videos/{videoId}/ratings`.
    *   Mock `rating_service.get_video_ratings_summary`.
    *   Test with no authentication token: `currentUserRating` should be `None`.
    *   Test with a valid token for a user who has rated the video: `currentUserRating` should have a value.
    *   Test with a valid token for a user who has NOT rated the video: `currentUserRating` should be `None`.
    *   Test video not found (service raises 404).

Current Files to Work On:
*   `app/services/rating_service.py`
*   `app/api/v1/endpoints/comments_ratings.py`
*   `app/api/v1/dependencies.py` (Crucial changes for optional authentication)
*   `tests/services/test_rating_service.py`
*   `tests/api/v1/test_dependencies.py`
*   `tests/api/v1/endpoints/test_comments_ratings.py`

Provide the complete content for each new/modified file.
```