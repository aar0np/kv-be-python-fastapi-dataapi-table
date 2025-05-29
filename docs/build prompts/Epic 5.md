Okay, we've completed "Comments & Ratings." The next logical step according to the API specification is **Section 5: Recommendations**. This involves content-based related lists and personalized "For You" recommendations, along with an endpoint for ingesting vector embeddings.

For this iteration, we will focus on the structure and stubs for these endpoints. Actual recommendation logic (content-based similarity, personalization) and vector embedding generation/ingestion are complex AI/ML tasks that often involve external services or significant backend processing. We'll set up the API contracts and placeholder service logic.

---

**Phase 1: Epic 5 - Recommendations (Stubs & API Structure)**
*Goal: Define models and implement API endpoints for video recommendations and vector embedding ingestion, with stubbed service logic. This sets the stage for future AI/ML integration.*

  *   **Chunk 5.1: Recommendation Models & Related Videos Endpoint (Stub)**
      *   **Step 5.1.1:** Create `app/models/recommendation.py`:
          *   Import `BaseModel, Field` from `pydantic`, `Optional, List` from `typing`.
          *   Import `VideoID` (from common or `app.models.video`).
          *   Import `HttpUrl` from `pydantic`.
          *   Define `class RecommendationItem(BaseModel)`: `videoId: VideoID`, `title: str`, `thumbnailUrl: Optional[HttpUrl] = None`, `score: Optional[float] = None` (relevance score).
      *   **Step 5.1.2:** Create `app/services/recommendation_service.py`:
          *   Import `Optional, List` from `typing`.
          *   Import `VideoID, VideoSummary` from `app/models.video`.
          *   Import `RecommendationItem` from `app.models.recommendation`.
          *   Import `video_service` from `app.services`.
          *   Implement `async def get_related_videos(video_id: VideoID, limit: int = 10) -> List[RecommendationItem]`:
              *   `# TODO: Implement actual content-based similarity logic.`
              *   `# For now, as a stub, fetch some latest videos (excluding video_id itself) and format them.`
              *   `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video`, return `[]`.
              *   `latest_videos_summary, _ = await video_service.list_latest_videos(page=1, page_size=limit + 5) # Fetch a bit more to filter`.
              *   `related_items = []`.
              *   `for vid_summary in latest_videos_summary:`
                  *   `if vid_summary.videoId != video_id and len(related_items) < limit:`
                      *   `related_items.append(RecommendationItem(videoId=vid_summary.videoId, title=vid_summary.title, thumbnailUrl=vid_summary.thumbnailUrl, score=round(random.uniform(0.5, 1.0), 2))) # Placeholder score`
              *   `import random` will be needed.
              *   Return `related_items`.
      *   **Step 5.1.3:** Create `app/api/v1/endpoints/recommendations.py`:
          *   Import `APIRouter, Depends, Query` from `fastapi`.
          *   Import `VideoID` from `app.models.video`.
          *   Import `RecommendationItem` from `app.models.recommendation`.
          *   Import `recommendation_service` from `app.services`.
          *   Import `List, Annotated` from `typing`.
          *   Initialize `router = APIRouter(prefix="/recommendations", tags=["Recommendations"])`.
          *   Implement `GET /videos/{videoId}/related` endpoint (Note: API spec path is `/videos/{videoId}/related`, so this should be part of `video_catalog.py` router, or a new router that can take this specific path. For simplicity of a new "Recommendations" service, we can start it here with `/videos/{videoId}/related` prefix, or adjust later. Let's put it in `recommendations.py` for now, path `/videos/{video_id_path}/related`).
              *   The API specification places `/videos/{videoId}/related` under "Recommendations" but its path structure suggests it could be related to the `video_catalog` router. To keep logical service separation for "Recommendations" but match the path, we can have `recommendations.router` handle paths that start with `/recommendations` AND this specific one. Alternatively, add to `video_catalog.router`.
              *   Let's choose to add to `video_catalog.router` for path consistency as it relates to a specific video resource.
      *   **Step 5.1.3 (Revised):** Modify `app/api/v1/endpoints/video_catalog.py` (instead of new `recommendations.py` for this specific endpoint):
          *   Import `RecommendationItem` from `app/models.recommendation`.
          *   Import `recommendation_service` from `app.services`.
          *   Import `List, Annotated` from `typing`.
          *   Implement `GET /{video_id_path}/related` endpoint within the existing `video_catalog.router`:
              *   Path operation: `@router.get("/{video_id_path}/related", response_model=List[RecommendationItem], summary="Content-based related list")`. Public.
              *   Signature: `async def get_related_videos_for_video(video_id_path: VideoID, limit: Annotated[int, Query(5, ge=1, le=20, description="Max number of related videos")] = 5)`.
              *   Call `related_items = await recommendation_service.get_related_videos(video_id=video_id_path, limit=limit)`.
              *   Return `related_items`.
      *   **Step 5.1.4:** Tests:
          *   Create `tests/models/test_recommendation.py` (if any validation needed, likely not for this simple model).
          *   Create `tests/services/test_recommendation_service.py`: Unit test `get_related_videos` (stubbed logic). Mock `video_service` calls. Verify it returns a list of `RecommendationItem` and respects the limit and excludes the source video.
          *   In `tests/api/v1/endpoints/test_video_catalog.py`: Add integration tests for `GET /api/v1/videos/{videoId}/related`. Mock `recommendation_service.get_related_videos`. Test with different limits. Test for non-existent source video ID.

  *   **Chunk 5.2: Personalized "For You" Endpoint (Stub)**
      *   **Step 5.2.1:** Modify `app/services/recommendation_service.py`:
          *   Import `User` from `app/models.user`.
          *   Import `VideoSummary` from `app.models.video`. (Already there).
          *   Import `Tuple` from `typing`.
          *   Implement `async def get_personalized_for_you_videos(current_user: User, page: int, page_size: int) -> Tuple[List[VideoSummary], int]`:
              *   `# TODO: Implement actual personalized recommendation logic (e.g., collaborative filtering, user history).`
              *   `# For now, as a stub, return some latest videos (could be a different set than generic latest).`
              *   `print(f"STUB: Generating 'For You' recommendations for user {current_user.userId}")`.
              *   `video_summaries, total_items = await video_service.list_latest_videos(page=page, page_size=page_size) # Reusing latest for stub`.
              *   `# Optionally, slightly randomize or modify the score/order to simulate personalization for testing`
              *   Return `(video_summaries, total_items)`.
      *   **Step 5.2.2:** Create `app/api/v1/endpoints/recommendations_feed.py` (or add to a general `recommendations.py` if preferred, but let's try a new file for a distinct "feed" concept).
          *   Import `APIRouter, Depends` from `fastapi`.
          *   Import `VideoSummary` from `app/models.video`.
          *   Import `PaginatedResponse, Pagination` from `app/models.common`.
          *   Import `PaginationParams, common_pagination_params, get_current_viewer` from `app.api.v1.dependencies`.
          *   Import `User` from `app.models.user`.
          *   Import `recommendation_service` from `app.services`.
          *   Import `Annotated` from `typing`.
          *   Initialize `router = APIRouter(prefix="/recommendations", tags=["Recommendations Feed"])`.
          *   Implement `GET /foryou` endpoint:
              *   Path operation: `@router.get("/foryou", response_model=PaginatedResponse[VideoSummary], summary="Personalized list (page,pageSize)")`.
              *   Protected by `current_user: Annotated[User, Depends(get_current_viewer)]`.
              *   Takes `pagination: Annotated[PaginationParams, Depends(common_pagination_params)]`.
              *   Call `summaries, total_items = await recommendation_service.get_personalized_for_you_videos(current_user=current_user, page=pagination.page, page_size=pagination.pageSize)`.
              *   Construct and return `PaginatedResponse`.
      *   **Step 5.2.3:** Modify `app/main.py` (or monolith entrypoint): Include `recommendations_feed.router`.
      *   **Step 5.2.4:** Tests:
          *   In `tests/services/test_recommendation_service.py`: Unit test `get_personalized_for_you_videos` (stubbed logic). Mock `video_service.list_latest_videos`.
          *   Create `tests/api/v1/endpoints/test_recommendations_feed.py`:
              *   Integration test `GET /api/v1/recommendations/foryou`. Mock `recommendation_service.get_personalized_for_you_videos`.
              *   Test with "viewer" token and pagination.
              *   Test without token (expect 401).

  *   **Chunk 5.3: Vector Embedding Ingestion Endpoint (Stub)**
      *   **Step 5.3.1:** Modify `app/models/recommendation.py`:
          *   Define `class EmbeddingIngestRequest(BaseModel)`: `videoId: VideoID`, `vector: List[float]` (or appropriate type for your embeddings).
          *   Define `class EmbeddingIngestResponse(BaseModel)`: `videoId: VideoID`, `status: str` (e.g., "received", "processed").
      *   **Step 5.3.2:** Modify `app/services/recommendation_service.py`:
          *   Import `EmbeddingIngestRequest, EmbeddingIngestResponse` from `app.models.recommendation`.
          *   Implement `async def ingest_video_embedding(request: EmbeddingIngestRequest) -> EmbeddingIngestResponse`:
              *   `# TODO: Implement logic to store/update the video's vector embedding in a vector DB or alongside video metadata.`
              *   `# This might involve calling video_service to update the video document or a separate vector store.`
              *   `print(f"STUB: Received embedding for video {request.videoId}. Vector dimension: {len(request.vector)}")`.
              *   `# For now, check if video exists (optional step for stub)`
              *   `target_video = await video_service.get_video_by_id(request.videoId)`.
              *   `if not target_video: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {request.videoId} not found for embedding ingestion")` (Need `HTTPException, status` from `fastapi`).
              *   Return `EmbeddingIngestResponse(videoId=request.videoId, status="received_stub")`.
      *   **Step 5.3.3:** Modify `app/api/v1/endpoints/recommendations_feed.py` (or the general `recommendations.py` if created). Let's assume it goes into `recommendations_feed.router` for now.
          *   Import `EmbeddingIngestRequest, EmbeddingIngestResponse` from `app/models.recommendation`.
          *   Import `get_current_creator` from `app.api.v1.dependencies` (API spec says "creator" auth for `/reco/ingest`).
          *   Implement `POST /reco/ingest` endpoint (path is `/reco/ingest` which is different from the router prefix `/recommendations`. This might need its own small router or careful pathing. If under `recommendations_feed.router` with prefix `/recommendations`, the path would be `/ingest-embedding` or similar. The spec says `/reco/ingest`. Let's make a new small router for `/reco`.)
      *   **Step 5.3.3 (Revised):** Create `app/api/v1/endpoints/reco_internal.py`:
          *   Import `APIRouter, Depends` from `fastapi`.
          *   Import `EmbeddingIngestRequest, EmbeddingIngestResponse` from `app.models.recommendation`.
          *   Import `User` from `app.models.user`.
          *   Import `get_current_creator` from `app.api.v1.dependencies`.
          *   Import `recommendation_service` from `app.services`.
          *   Import `Annotated` from `typing`.
          *   Initialize `router = APIRouter(prefix="/reco", tags=["Reco Internal"])`.
          *   Implement `POST /ingest` endpoint:
              *   Path operation: `@router.post("/ingest", response_model=EmbeddingIngestResponse, summary="Ingest vector embedding for new video")`.
              *   Protected by `current_user: Annotated[User, Depends(get_current_creator)]`.
              *   Takes `request: EmbeddingIngestRequest`.
              *   Call `response = await recommendation_service.ingest_video_embedding(request=request)`.
              *   Return `response`.
      *   **Step 5.3.4:** Modify `app/main.py` (or monolith entrypoint): Include `reco_internal.router`.
      *   **Step 5.3.5:** Tests:
          *   In `tests/services/test_recommendation_service.py`: Unit test `ingest_video_embedding` (stubbed logic). Mock `video_service.get_video_by_id`.
          *   Create `tests/api/v1/endpoints/test_reco_internal.py`:
              *   Integration test `POST /api/v1/reco/ingest`. Mock `recommendation_service.ingest_video_embedding`.
              *   Test with "creator" token and valid payload.
              *   Test with "viewer" token (expect 403).
              *   Test request body validation.

---

This completes the plan for Epic 5. I'll now generate the LLM prompts.

## LLM Prompts - Iteration 5 (Epic 5: Recommendations - Stubs)

---
**Prompt 20 (was 5.1): Recommendation Models & Related Videos Endpoint (Stub)**
```text
Objective: Define models for video recommendations and implement a stubbed public endpoint to get videos related to a given video. The actual recommendation logic will be a placeholder.

Specifications:
1.  Create `app/models/recommendation.py`:
    *   Import `BaseModel, Field, HttpUrl` from `pydantic`, `Optional, List` from `typing`.
    *   Attempt to import `VideoID` from `app.models.video` (if not centralized, define as `VideoID = UUID` and import `UUID`).
    *   Define `class RecommendationItem(BaseModel)`: `videoId: VideoID`, `title: str`, `thumbnailUrl: Optional[HttpUrl] = None`, `score: Optional[float] = Field(None, ge=0, le=1, description="Relevance score, if available")`.
2.  Create `app/services/recommendation_service.py`:
    *   Import `Optional, List, random` from `typing` and `random`.
    *   Import `VideoID, VideoSummary` from `app.models.video`.
    *   Import `RecommendationItem` from `app.models.recommendation`.
    *   Import `video_service` from `app.services`.
    *   Implement `async def get_related_videos(video_id: VideoID, limit: int = 10) -> List[RecommendationItem]`:
        *   `# STUB IMPLEMENTATION: Fetches latest videos, excludes the source video, and adds a random score.`
        *   Call `target_video = await video_service.get_video_by_id(video_id)`. If not `target_video`, return `[]`.
        *   Call `latest_videos_summaries, _ = await video_service.list_latest_videos(page=1, page_size=limit + 5) # Fetch a bit more to ensure enough items after filtering`.
        *   Initialize `related_items: List[RecommendationItem] = []`.
        *   Loop through `latest_videos_summaries`:
            *   If `vid_summary.videoId != video_id` and `len(related_items) < limit`:
                *   `related_items.append(RecommendationItem(videoId=vid_summary.videoId, title=vid_summary.title, thumbnailUrl=vid_summary.thumbnailUrl, score=round(random.uniform(0.5, 1.0), 2)))`.
        *   Return `related_items`.
3.  Modify `app/api/v1/endpoints/video_catalog.py` (to keep the path `/videos/{videoId}/related` cohesive with video resources):
    *   Import `RecommendationItem` from `app/models.recommendation`.
    *   Import `recommendation_service` from `app.services`.
    *   Import `List, Annotated` from `typing` (if not already).
    *   Import `Query` from `fastapi` (if not already).
    *   Import `VideoID` from `app.models.video` (if not already).
    *   Implement `GET /{video_id_path}/related` endpoint within the existing `video_catalog.router`:
        *   Decorator: `@router.get("/{video_id_path}/related", response_model=List[RecommendationItem], summary="Get content-based related videos list")`. Public.
        *   Signature: `async def get_related_videos_list(video_id_path: VideoID, limit: Annotated[int, Query(5, ge=1, le=20, description="Maximum number of related videos")] = 5)`.
        *   Call `related_items = await recommendation_service.get_related_videos(video_id=video_id_path, limit=limit)`.
        *   Return `related_items`.
4.  Create `tests/services/test_recommendation_service.py`:
    *   Import `pytest`, `unittest.mock.AsyncMock`, `unittest.mock.patch`.
    *   Import `get_related_videos` service function and relevant models (`Video`, `VideoSummary`, `RecommendationItem`).
    *   Test `get_related_videos`:
        *   Mock `video_service.get_video_by_id` and `video_service.list_latest_videos`.
        *   Test that it returns a list of `RecommendationItem`.
        *   Test that the `limit` parameter is respected.
        *   Test that the source `video_id` is excluded from results.
        *   Test when source video is not found (returns empty list).
5.  In `tests/api/v1/endpoints/test_video_catalog.py`:
    *   Add integration tests for `GET /api/v1/videos/{videoId}/related`.
    *   Mock `recommendation_service.get_related_videos`.
    *   Test successful response with data.
    *   Test `limit` query parameter.
    *   Test with a non-existent source `videoId` (mock service to return empty list or handle as per service logic).

Current Files to Work On:
*   `app/models/recommendation.py`
*   `app/services/recommendation_service.py`
*   `app/api/v1/endpoints/video_catalog.py`
*   `tests/services/test_recommendation_service.py`
*   `tests/api/v1/endpoints/test_video_catalog.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 21 (was 5.2): Personalized "For You" Endpoint (Stub)**
```text
Objective: Implement a stubbed endpoint for personalized "For You" video recommendations, requiring "viewer" authentication.

Specifications:
1.  Modify `app/services/recommendation_service.py`:
    *   Import `User` from `app.models.user`.
    *   Import `VideoSummary` from `app.models.video` (if not already).
    *   Import `Tuple` from `typing` (if not already).
    *   (Ensure `video_service` is imported).
    *   Implement `async def get_personalized_for_you_videos(current_user: User, page: int, page_size: int) -> Tuple[List[VideoSummary], int]`:
        *   `# STUB IMPLEMENTATION: Returns latest videos for now, pretending it's personalized.`
        *   `print(f"STUB: Generating 'For You' recommendations for user {current_user.userId} (page: {page}, pageSize: {page_size})")`.
        *   `video_summaries, total_items = await video_service.list_latest_videos(page=page, page_size=page_size)`.
        *   `# Optional: Could slightly modify or re-score summaries here to differentiate from generic latest for testing.`
        *   Return `(video_summaries, total_items)`.
2.  Create `app/api/v1/endpoints/recommendations_feed.py`:
    *   Import `APIRouter, Depends` from `fastapi`.
    *   Import `VideoSummary` from `app/models.video`.
    *   Import `PaginatedResponse, Pagination` from `app/models.common`.
    *   Import `PaginationParams, common_pagination_params, get_current_viewer` from `app.api.v1.dependencies`.
    *   Import `User` from `app/models.user`.
    *   Import `recommendation_service` from `app.services`.
    *   Import `Annotated, List` from `typing`.
    *   Initialize `router = APIRouter(prefix="/recommendations", tags=["Recommendations"])` (Changed tag to general "Recommendations" as it will hold more).
    *   Implement `GET /foryou` endpoint:
        *   Decorator: `@router.get("/foryou", response_model=PaginatedResponse[VideoSummary], summary="Get personalized 'For You' video recommendations")`.
        *   Signature: `async def get_for_you_feed(pagination: Annotated[PaginationParams, Depends(common_pagination_params)], current_user: Annotated[User, Depends(get_current_viewer)])`.
        *   Call `summaries, total_items = await recommendation_service.get_personalized_for_you_videos(current_user=current_user, page=pagination.page, page_size=pagination.pageSize)`.
        *   Construct `total_pages` and return `PaginatedResponse` (as in previous list endpoints).
3.  Modify `app/main.py` (or monolith entrypoint):
    *   Import `recommendations_feed_router` (rename `router` in `recommendations_feed.py`).
    *   Include it in `api_router_v1`: `api_router_v1.include_router(recommendations_feed.router)`.
4.  In `tests/services/test_recommendation_service.py`:
    *   Add unit tests for `get_personalized_for_you_videos` (stubbed logic).
    *   Mock `video_service.list_latest_videos`. Verify it's called and its results are returned.
5.  Create `tests/api/v1/endpoints/test_recommendations_feed.py`:
    *   Import `AsyncClient`, `status`, relevant models.
    *   Write integration tests for `GET /api/v1/recommendations/foryou`:
        *   Mock `recommendation_service.get_personalized_for_you_videos`.
        *   Use helper to get JWT for "viewer".
        *   Test successful response with pagination.
        *   Test access without token (expect 401, handled by `get_current_viewer` if `get_current_user_from_token` is not optional there. If `get_current_user_from_token` is optional, `get_current_viewer` should still enforce auth).

Current Files to Work On:
*   `app/services/recommendation_service.py`
*   `app/api/v1/endpoints/recommendations_feed.py`
*   `app/main.py`
*   `tests/services/test_recommendation_service.py`
*   `tests/api/v1/endpoints/test_recommendations_feed.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 22 (was 5.3): Vector Embedding Ingestion Endpoint (Stub)**
```text
Objective: Implement a stubbed endpoint for "creators" to ingest vector embeddings for videos, preparing for future AI-powered recommendations.

Specifications:
1.  Modify `app/models/recommendation.py`:
    *   Import `VideoID` (if not already).
    *   Import `List` from `typing`.
    *   Define `class EmbeddingIngestRequest(BaseModel)`: `videoId: VideoID`, `vector: List[float] = Field(..., description="The vector embedding for the video content.")`.
    *   Define `class EmbeddingIngestResponse(BaseModel)`: `videoId: VideoID`, `status: str`, `message: Optional[str] = None`.
2.  Modify `app/services/recommendation_service.py`:
    *   Import `EmbeddingIngestRequest, EmbeddingIngestResponse` from `app/models.recommendation`.
    *   Import `HTTPException, status` from `fastapi`. (If not already imported).
    *   (Ensure `video_service` is imported).
    *   Implement `async def ingest_video_embedding(request: EmbeddingIngestRequest) -> EmbeddingIngestResponse`:
        *   `# STUB IMPLEMENTATION: Simulates receiving an embedding.`
        *   `# In a real scenario, this would store the vector in a specialized vector database`
        *   `# or update the video document in AstraDB if it has a vector field.`
        *   Call `target_video = await video_service.get_video_by_id(request.videoId)`.
        *   If not `target_video`:
            *   `return EmbeddingIngestResponse(videoId=request.videoId, status="error", message=f"Video {request.videoId} not found.")`
            *   (Alternatively, raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {request.videoId} not found.")` - choose one approach. Let's return a response object for this specific case as per `EmbeddingIngestResponse` structure).
        *   `print(f"STUB: Received embedding for video {request.videoId}. Vector dimension: {len(request.vector)}. First 3 dims: {request.vector[:3]}")`.
        *   `# TODO: Add logic to update video_doc with embedding_processed_at timestamp or similar.`
        *   Return `EmbeddingIngestResponse(videoId=request.videoId, status="received_stub", message="Embedding data received and acknowledged (stub).")`.
3.  Create `app/api/v1/endpoints/reco_internal.py` (for the distinct `/reco` path prefix):
    *   Import `APIRouter, Depends, status` from `fastapi`.
    *   Import `EmbeddingIngestRequest, EmbeddingIngestResponse` from `app/models.recommendation`.
    *   Import `User` from `app.models.user`.
    *   Import `get_current_creator` from `app.api.v1.dependencies`.
    *   Import `recommendation_service` from `app.services`.
    *   Import `Annotated` from `typing`.
    *   Initialize `router = APIRouter(prefix="/reco", tags=["Recommendations Internal"])`.
    *   Implement `POST /ingest` endpoint:
        *   Decorator: `@router.post("/ingest", response_model=EmbeddingIngestResponse, status_code=status.HTTP_202_ACCEPTED, summary="Ingest vector embedding for a video")`.
        *   Signature: `async def ingest_embedding(request: EmbeddingIngestRequest, current_user: Annotated[User, Depends(get_current_creator)])`.
        *   Call `response = await recommendation_service.ingest_video_embedding(request=request)`.
        *   If `response.status == "error" and "not found" in (response.message or "")`: # Check if service indicated video not found
            `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.message)`
        *   Return `response`.
4.  Modify `app/main.py` (or monolith entrypoint):
    *   Import `reco_internal_router` (rename `router` in `reco_internal.py`).
    *   Include it in `api_router_v1`: `api_router_v1.include_router(reco_internal.router)`.
5.  In `tests/services/test_recommendation_service.py`:
    *   Add unit tests for `ingest_video_embedding` (stubbed logic).
    *   Mock `video_service.get_video_by_id`.
    *   Test scenario where video exists.
    *   Test scenario where video does not exist (service returns specific response).
6.  Create `tests/api/v1/endpoints/test_reco_internal.py`:
    *   Import `AsyncClient`, `status`, relevant models.
    *   Write integration tests for `POST /api/v1/reco/ingest`:
        *   Mock `recommendation_service.ingest_video_embedding`.
        *   Use helper to get JWT for "creator".
        *   Test successful ingestion: mock service to return success `EmbeddingIngestResponse`. Assert `202 ACCEPTED`.
        *   Test ingestion for non-existent video: mock service to return error `EmbeddingIngestResponse` indicating video not found. Assert `404 NOT FOUND` from the endpoint.
        *   Test access with "viewer" token (expect 403).
        *   Test request body validation (e.g., missing `videoId` or `vector`).

Current Files to Work On:
*   `app/models/recommendation.py`
*   `app/services/recommendation_service.py`
*   `app/api/v1/endpoints/reco_internal.py`
*   `app/main.py`
*   `tests/services/test_recommendation_service.py`
*   `tests/api/v1/endpoints/test_reco_internal.py`

Provide the complete content for each new/modified file.
```