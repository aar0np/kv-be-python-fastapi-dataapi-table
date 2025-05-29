Okay, we've completed the core Video Catalog features. Next, we'll move on to implementing **Search** functionalities as outlined in the API Specification (Section 3: Search) and Functional Specification (FR-SE-001 - FR-SE-003).

This epic is relatively small, focusing on video search and tag suggestions. We'll assume for the keyword search that it's a basic text search against video titles/descriptions/tags for now. The "vector hybrid search" mentioned in the API spec is a more advanced feature that would typically require integration with a vector database or search engine with vector capabilities (Astra DB does support this). For this iteration, we'll implement a simpler keyword search, and the groundwork for vector search can be added later.

---

**Phase 1: Epic 3 - Search Functionality**
*Goal: Implement keyword-based video search and tag autocompletion.*

  *   **Chunk 3.1: Search Models & Basic Video Search Endpoint**
      *   **Step 3.1.1:** Modify `app/models/video.py`: (No new models strictly for search requests, but `VideoSummary` will be reused for search results).
      *   **Step 3.1.2:** Modify `app/services/video_service.py`:
          *   Import `VideoSummary` from `app/models/video`.
          *   Implement `async def search_videos_by_keyword(query: str, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
              *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
              *   Construct a query filter for AstraDB's Data API. This will depend on how AstraDB handles text search on JSON documents. A common approach for basic search might be to use `$regex` (if supported and performant enough for your dataset size) on `title`, `description`, and `tags` fields. For example, a filter might look something like (this is pseudo-syntax, adapt to actual `astrapy` Data API capabilities):
                  ```python
                  search_filter = {
                      "status": VideoStatusEnum.READY, # Only search ready videos
                      "$or": [
                          {"title": {"$regex": query, "$options": "i"}}, # case-insensitive
                          {"description": {"$regex": query, "$options": "i"}},
                          {"tags": {"$regex": query, "$options": "i"}} # search if query substring is in any tag
                      ]
                  }
                  ```
                  *Note: Full-text search capabilities in Astra DB via the Data API might be limited. If a more robust text search is needed, creating a search index (e.g., a SAI index if using CQL, or specific indexing for Data API if available) would be required. For vector hybrid search later, this service method would be significantly different.*
              *   Use the existing `list_videos_with_query` helper function if suitable, passing this `search_filter`. Sorting might be by relevance if the DB supports it, or fallback to `submittedAt` descending.
              *   Return `List[VideoSummary]` and total count matching the search.
      *   **Step 3.1.3:** Create `app/api/v1/endpoints/search_catalog.py` (or just `search.py`):
          *   Import `APIRouter, Depends` from `fastapi`.
          *   Import `VideoSummary` from `app/models/video`, `PaginatedResponse, Pagination` from `app/models/common`.
          *   Import `PaginationParams, common_pagination_params` from `app/api/v1.dependencies`.
          *   Import `video_service` from `app.services`.
          *   Import `Annotated` from `typing`.
          *   Initialize `router = APIRouter(prefix="/search", tags=["Search"])`.
          *   Implement `GET /videos` endpoint (maps to `/search/videos`):
              *   Path operation: `@router.get("/videos", response_model=PaginatedResponse[VideoSummary], summary="Keyword + vector hybrid search (query)")`. (For now, only keyword).
              *   Public endpoint.
              *   Takes `query: str = Query(..., min_length=1, description="Search query term")` and `pagination: Annotated[PaginationParams, Depends(common_pagination_params)]`.
              *   Calls `summaries, total_items = await video_service.search_videos_by_keyword(query=query, page=pagination.page, page_size=pagination.pageSize)`.
              *   Constructs and returns `PaginatedResponse` (similar to list endpoints).
      *   **Step 3.1.4:** Modify `app/main.py` (or monolith entrypoint): Include `search_catalog.router`.
      *   **Step 3.1.5:** Tests:
          *   Write unit tests in `tests/services/test_video_service.py` for `search_videos_by_keyword`. Mock DB calls. Verify the filter construction and that it calls `list_videos_with_query` or equivalent DB find method correctly.
          *   Create `tests/api/v1/endpoints/test_search_catalog.py`. Write integration tests for `GET /api/v1/search/videos`:
              *   Mock `video_service.search_videos_by_keyword`.
              *   Test with a query term and pagination.
              *   Test with missing `query` parameter (expect 422).
              *   Test empty search results.

  *   **Chunk 3.2: Tag Suggestion Endpoint**
      *   **Step 3.2.1:** Modify `app/models/video.py` (or create `app/models/tag.py` if it grows):
          *   Define `class TagSuggestion(BaseModel)`: `tag: str`, `count: Optional[int] = None` (count could be how many videos use this tag, if feasible to compute).
      *   **Step 3.2.2:** Modify `app/services/video_service.py`:
          *   Import `TagSuggestion` from `app/models.video`.
          *   Implement `async def suggest_tags(query: str, limit: int = 10, db_table: Optional[AstraDBCollection] = None) -> List[TagSuggestion]`:
              *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
              *   This is a bit more complex with a typical document DB / Data API if you don't have specific aggregation framework support through `astrapy` for this use case.
              *   **Option 1 (Simpler, less performant for large datasets):** Fetch all distinct tags first, then filter in Python.
                  *   `# distinct_tags_cursor = await db_table.distinct("tags", filter={"status": VideoStatusEnum.READY})` (Check `astrapy` for `distinct` method or equivalent aggregation).
                  *   `# all_tags = await distinct_tags_cursor.to_list(length=None)` (or however distinct values are retrieved).
                  *   `# matching_tags = [t for t in all_tags if query.lower() in t.lower()]`
                  *   `# suggestions = [TagSuggestion(tag=t) for t in matching_tags[:limit]]`
              *   **Option 2 (More performant if DB supports regex on array elements and aggregation):**
                  *   Use an aggregation pipeline if `astrapy` Data API allows it: unwind tags, match query, group by tag, count, sort, limit. This is unlikely to be straightforward with basic Data API JSON commands unless `astrapy` abstracts it.
                  *   **For now, implement Option 1 for simplicity.** If `distinct` is not available or too slow, this feature might require a different data model for tags (e.g., a separate 'tags' table/collection) or rely on an external search engine's faceting/autocomplete features.
              *   Return the list of `TagSuggestion` objects.
      *   **Step 3.2.3:** Modify `app/api/v1/endpoints/search_catalog.py`:
          *   Import `TagSuggestion` from `app/models.video`.
          *   Import `List` from `typing`.
          *   Implement `GET /tags/suggest` endpoint (maps to `/search/tags/suggest`):
              *   Path operation: `@router.get("/tags/suggest", response_model=List[TagSuggestion], summary="Autocomplete tags (query, limit)")`.
              *   Public endpoint.
              *   Takes `query: str = Query(..., min_length=1, description="Partial tag to search for")` and `limit: int = Query(10, ge=1, le=25, description="Maximum number of suggestions")`.
              *   Calls `suggestions = await video_service.suggest_tags(query=query, limit=limit)`.
              *   Returns `suggestions`.
      *   **Step 3.2.4:** Tests:
          *   Write unit tests in `tests/services/test_video_service.py` for `suggest_tags`. Mock DB calls (e.g., `distinct` if used, or `find` if iterating). Test query matching and limit.
          *   Update integration tests in `tests/api/v1/endpoints/test_search_catalog.py` for `GET /api/v1/search/tags/suggest`:
              *   Mock `video_service.suggest_tags`.
              *   Test with a query and limit.
              *   Test with missing `query` (expect 422).

---

This completes the plan for Epic 3: Search. I'll now generate the LLM prompts.

## LLM Prompts - Iteration 3 (Epic 3: Search Functionality)

---
**Prompt 14 (was 3.1): Basic Video Keyword Search Endpoint**
```text
Objective: Implement a public endpoint for keyword-based search across video titles, descriptions, and tags.

Specifications:
1.  Verify `app/models/video.py`: Ensure `VideoSummary` model is available for search results. No new models are strictly needed for this step.
2.  Modify `app/services/video_service.py`:
    *   Import `Tuple, List, Dict, Any, Optional` from `typing`.
    *   Import `VideoSummary, VideoStatusEnum` from `app/models/video`.
    *   Import `AstraDBCollection` from `astrapy.db`.
    *   Ensure `VIDEOS_TABLE_NAME` constant is defined.
    *   (If not already present) Implement a generic `async def list_videos_with_query(query_filter: Dict[str, Any], page: int, page_size: int, sort_options: Optional[Dict[str, Any]] = None, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]` as defined in Prompt 13, Step 3 (it fetches videos based on a filter, paginates, sorts, maps to VideoSummary, and returns summaries + total_items).
    *   Implement `async def search_videos_by_keyword(query: str, page: int, page_size: int, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[VideoSummary], int]`:
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   Construct `search_filter`:
            ```python
            # This assumes AstraDB Data API supports $regex and $or in a way compatible with astrapy.
            # Adapt if astrapy requires a different syntax for complex queries.
            # For true full-text search, an index would be needed on the DB side.
            # This is a basic keyword-matching approach.
            escaped_query = re.escape(query) # Escape regex special characters in user query
            search_filter = {
                "status": VideoStatusEnum.READY.value, # Ensure enum value is used for query
                "$or": [
                    {"title": {"$regex": escaped_query, "$options": "i"}},
                    {"description": {"$regex": escaped_query, "$options": "i"}},
                    {"tags": {"$regex": escaped_query, "$options": "i"}} # Matches if any tag contains the query term
                ]
            }
            ```
            *   (You'll need `import re`).
        *   Call `return await list_videos_with_query(query_filter=search_filter, page=page, page_size=page_size, sort_options={"submittedAt": -1}, db_table=db_table)`. (Default sort by submission date; relevance sorting is more complex).
3.  Create `app/api/v1/endpoints/search_catalog.py`:
    *   Import `APIRouter, Depends, Query` from `fastapi`.
    *   Import `VideoSummary` from `app/models/video`.
    *   Import `PaginatedResponse, Pagination` from `app/models/common`.
    *   Import `PaginationParams, common_pagination_params` from `app/api/v1.dependencies`.
    *   Import `video_service` from `app.services`.
    *   Import `Annotated` from `typing`.
    *   Initialize `router = APIRouter(prefix="/search", tags=["Search"])`.
    *   Implement `GET /videos` endpoint:
        *   Decorator: `@router.get("/videos", response_model=PaginatedResponse[VideoSummary], summary="Keyword video search")`.
        *   Signature: `async def search_videos(query: Annotated[str, Query(min_length=1, description="Search query term")], pagination: Annotated[PaginationParams, Depends(common_pagination_params)])`.
        *   Call `summaries, total_items = await video_service.search_videos_by_keyword(query=query, page=pagination.page, page_size=pagination.pageSize)`.
        *   Construct `total_pages` and return `PaginatedResponse` (as in previous list endpoints).
4.  Modify `app/main.py` (or monolith entrypoint):
    *   Import `search_catalog_router` (rename `router` in `search_catalog.py`).
    *   Include it in `api_router_v1`: `api_router_v1.include_router(search_catalog.router)`.
5.  In `tests/services/test_video_service.py`:
    *   Add unit tests for `search_videos_by_keyword`.
    *   Mock `list_videos_with_query` or mock the DB calls directly (`get_table`, `AstraDBCollection.find`, `AstraDBCollection.count_documents`).
    *   Verify the structure of `search_filter` passed to underlying query methods, especially the `$or` and `$regex` parts.
6.  Create `tests/api/v1/endpoints/test_search_catalog.py`:
    *   Import `AsyncClient`, `status`.
    *   Write integration tests for `GET /api/v1/search/videos`:
        *   Mock `video_service.search_videos_by_keyword`.
        *   Test with a valid query and pagination: mock service to return sample data. Assert `200 OK` and paginated response.
        *   Test with `query` parameter missing or empty (FastAPI `Query(min_length=1)` should handle this): Assert `422 Unprocessable Entity`.
        *   Test scenario where service returns no matching videos.

Current Files to Work On:
*   `app/services/video_service.py`
*   `app/api/v1/endpoints/search_catalog.py`
*   `app/main.py`
*   `tests/services/test_video_service.py`
*   `tests/api/v1/endpoints/test_search_catalog.py`

Provide the complete content for each new/modified file. Note any assumptions about `astrapy`'s handling of `$regex` or complex queries.
```
---
**Prompt 15 (was 3.2): Tag Suggestion Endpoint**
```text
Objective: Implement an endpoint for tag autocompletion suggestions based on existing video tags.

Specifications:
1.  Modify `app/models/video.py` (or create `app/models/tag.py` if preferred, for now keep in `video.py`):
    *   Import `BaseModel`, `Optional` from `pydantic`, `List` from `typing`.
    *   Define `class TagSuggestion(BaseModel)`: `tag: str`. (Count is omitted for simplicity for now as it's harder with basic Data API).
2.  Modify `app/services/video_service.py`:
    *   Import `TagSuggestion` from `app/models.video`.
    *   Implement `async def suggest_tags(query: str, limit: int = 10, db_table: Optional[AstraDBCollection] = None) -> List[TagSuggestion]`:
        *   If `db_table` is None, `db_table = await get_table(VIDEOS_TABLE_NAME)`.
        *   Attempt to fetch distinct tags. The `distinct()` method in `astrapy` for the Data API might not be directly available or might work differently than in MongoDB drivers.
        *   **Primary approach (if `distinct` is available and efficient for `astrapy`):**
            ```python
            # Example assuming astrapy has a distinct-like method or you know how to query distinct values:
            # This is pseudo-code for the distinct part. Actual implementation depends on astrapy.
            # Option A: If astrapy supports distinct directly on an array field:
            # distinct_tags_results = await db_table.distinct("tags", filter={"status": VideoStatusEnum.READY.value})
            # all_tags = [tag for tag in distinct_tags_results if isinstance(tag, str)] # Ensure they are strings

            # Option B: If distinct is not direct, or if it's better to fetch and process:
            # Fetch a limited number of recent/relevant videos and extract tags
            pipeline_for_distinct_tags = [
                {"$match": {"status": VideoStatusEnum.READY.value, "tags": {"$exists": True, "$ne": []}}}, # Videos with tags
                {"$unwind": "$tags"}, # Deconstruct the tags array
                {"$group": {"_id": "$tags"}}, # Group by tag name to get unique tags
                {"$project": {"tag": "$_id", "_id": 0}}, # Rename _id to tag
                {"$limit": 500} # Limit overall unique tags considered, adjust as needed for performance
            ]
            # Note: Aggregation pipeline support via astrapy's Data API client needs to be verified.
            # If not supported, this approach is not viable via astrapy Data API.
            # For now, let's assume a simpler fallback if aggregations or distinct on arrays are hard.

            # Fallback/Simpler approach (less performant on large datasets without good indexing/aggregation):
            # Fetch all tags from a subset of videos and make them unique in Python.
            all_tags_set = set()
            # Find videos with tags, limit initial fetch for performance.
            # The filter ensures tags field exists and is not empty.
            # Sort by submission date to get somewhat relevant recent tags.
            videos_with_tags_cursor = db_table.find(
                filter={"status": VideoStatusEnum.READY.value, "tags": {"$exists": True}}, # $exists might need checking for astrapy
                projection={"tags": 1}, # Only fetch the tags field
                limit=2000, # Limit how many video documents we scan for tags
                sort={"submittedAt": -1}
            )
            async for video_doc in videos_with_tags_cursor: # Iterate async if supported by astrapy cursor
                if video_doc and "tags" in video_doc and isinstance(video_doc["tags"], list):
                    for tag in video_doc["tags"]:
                        if isinstance(tag, str):
                           all_tags_set.add(tag)
            # End of Fallback
            ```
        *   Filter these `all_tags_set` (or `all_tags` from distinct) in Python:
            `matching_tags = sorted([t for t in all_tags_set if query.lower() in t.lower()])`
        *   Create suggestions: `suggestions = [TagSuggestion(tag=t) for t in matching_tags[:limit]]`.
        *   Return `suggestions`.
        *   **Clearly state in comments the chosen approach for fetching unique tags and its potential performance implications or `astrapy` dependencies.** For this prompt, implement the "Fallback/Simpler approach" (scan N video documents).
3.  Modify `app/api/v1/endpoints/search_catalog.py`:
    *   Import `TagSuggestion` from `app/models.video`.
    *   Import `List` from `typing`. (If not already present).
    *   Implement `GET /tags/suggest` endpoint:
        *   Decorator: `@router.get("/tags/suggest", response_model=List[TagSuggestion], summary="Autocomplete tags")`.
        *   Signature: `async def suggest_video_tags(query: Annotated[str, Query(min_length=1, description="Partial tag to search for")], limit: Annotated[int, Query(10, ge=1, le=25, description="Maximum number of suggestions")] = 10)`.
        *   Call `suggestions = await video_service.suggest_tags(query=query, limit=limit)`.
        *   Return `suggestions`.
4.  In `tests/services/test_video_service.py`:
    *   Add unit tests for `suggest_tags`.
    *   Mock DB calls (e.g., `AstraDBCollection.find` for the fallback approach).
    *   Prepare sample video documents with various tags.
    *   Test scenarios:
        *   Query matches some tags.
        *   Query matches no tags.
        *   `limit` parameter is respected.
        *   Case-insensitivity of matching.
5.  In `tests/api/v1/endpoints/test_search_catalog.py`:
    *   Add integration tests for `GET /api/v1/search/tags/suggest`:
        *   Mock `video_service.suggest_tags`.
        *   Test with a valid query and limit: mock service to return sample `TagSuggestion` list. Assert `200 OK` and correct response.
        *   Test with `query` parameter missing (FastAPI `Query(min_length=1)` should handle this): Assert `422 Unprocessable Entity`.
        *   Test when service returns an empty list.

Current Files to Work On:
*   `app/models/video.py` (or `app/models/tag.py`)
*   `app/services/video_service.py`
*   `app/api/v1/endpoints/search_catalog.py`
*   `tests/services/test_video_service.py`
*   `tests/api/v1/endpoints/test_search_catalog.py`

Provide the complete content for each new/modified file. Focus on the "Fallback/Simpler approach" for `suggest_tags` in the service layer, fetching tags from a limited set of video documents.
```