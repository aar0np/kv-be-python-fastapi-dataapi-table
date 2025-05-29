Excellent. We've laid the groundwork for Recommendations. Now, we'll address the final major section from the API specification: **Section 6: Moderator Role Management** and the content moderation aspects detailed in **Section 2 (Video Catalog & Moderation)** and **Functional Specification (FR-MO)**.

This epic will be substantial as it involves new roles, flagging content (videos/comments), managing flags, and moderator actions.

---

**Phase 1: Epic 6 - Content Moderation & Moderator Roles**
*Goal: Implement functionalities for users to flag content, for moderators to manage these flags, act on content, and for moderators to manage moderator roles for other users.*

  *   **Chunk 6.1: Flag Models, Generic Flag Endpoint & "Moderator" Role Setup**
      *   **Step 6.1.1:** Create `app/models/flag.py`:
          *   Import `BaseModel, Field` from `pydantic`, `Optional, List, Union` from `typing`, `UUID, uuid4` from `uuid`, `datetime` from `datetime`, `Enum` from `enum`.
          *   Import `VideoID` from `app.models.video`, `CommentID` from `app.models.comment`, `UserID` from `app.models.user`.
          *   Define `FlagID = UUID`.
          *   Define `ContentTypeEnum(str, Enum)`: `VIDEO = "video"`, `COMMENT = "comment"`.
          *   Define `FlagReasonCodeEnum(str, Enum)`: `SPAM = "spam"`, `INAPPROPRIATE = "inappropriate"`, `HARASSMENT = "harassment"`, `COPYRIGHT = "copyright"`, `OTHER = "other"`.
          *   Define `FlagStatusEnum(str, Enum)`: `OPEN = "open"`, `UNDER_REVIEW = "under_review"`, `APPROVED = "approved"` (flag is valid, content actioned), `REJECTED = "rejected"` (flag is invalid).
          *   Define `class FlagBase(BaseModel)`: `contentType: ContentTypeEnum`, `contentId: Union[VideoID, CommentID]` (Pydantic might need `Any` or careful use of `Union` here for validation if types are UUID), `reasonCode: FlagReasonCodeEnum`, `reasonText: Optional[str] = Field(None, max_length=500, description="Optional additional details for 'other' or specific cases")`.
          *   Define `class FlagCreateRequest(FlagBase)`: (No additional fields from base for user submission).
          *   Define `class Flag(FlagBase)`: `flagId: FlagID`, `userId: UserID` (who flagged it), `createdAt: datetime`, `updatedAt: datetime`, `status: FlagStatusEnum = FlagStatusEnum.OPEN`, `moderatorId: Optional[UserID] = None` (who actioned it), `moderatorNotes: Optional[str] = None`, `resolvedAt: Optional[datetime] = None`.
          *   Define `class FlagResponse(Flag)`: (Can `pass`).
          *   Define `class FlagUpdateRequest(BaseModel)`: `status: FlagStatusEnum`, `moderatorNotes: Optional[str] = Field(None, max_length=1000)`.
      *   **Step 6.1.2:** Modify `app/api/v1/dependencies.py`: Ensure `get_current_moderator` dependency is correctly defined using `require_role(["moderator"])`.
      *   **Step 6.1.3:** Modify `app/services/user_service.py` (Actual implementation for role assignment):
          *   Import `AstraDBCollection`, `get_table`, `USERS_TABLE_NAME`.
          *   Implement `async def assign_role_to_user(user_to_modify_id: UUID, role_to_assign: str, db_table: Optional[AstraDBCollection] = None) -> bool`:
              *   Fetches user by `user_to_modify_id`. If not found, return `False`.
              *   Appends `role_to_assign` to user's `roles` list if not already present (ensure roles are stored as a list in DB). Update user document.
              *   Return `True` on success.
          *   Implement `async def revoke_role_from_user(user_to_modify_id: UUID, role_to_revoke: str, db_table: Optional[AstraDBCollection] = None) -> bool`:
              *   Fetches user. If not found or role not present, return `False`.
              *   Removes `role_to_revoke` from user's `roles` list. Update user document.
              *   Return `True` on success.
      *   **Step 6.1.4:** Create `app/services/flag_service.py`:
          *   Import relevant models (`FlagCreateRequest`, `Flag`, `FlagID`, `ContentTypeEnum`, etc.), `User`, DB utilities.
          *   Import `video_service`, `comment_service` (to check content existence).
          *   Define `FLAGS_TABLE_NAME: str = "flags"`.
          *   Implement `async def create_flag(request: FlagCreateRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Flag`:
              *   Validate `contentId` existence:
                  *   If `request.contentType == ContentTypeEnum.VIDEO`, check `await video_service.get_video_by_id(request.contentId)`.
                  *   If `request.contentType == ContentTypeEnum.COMMENT`, check `await comment_service.get_comment_by_id(request.contentId)` (this service method needs to be created).
                  *   If content not found, raise `HTTPException 404`.
              *   If `db_table` is None, `db_table = await get_table(FLAGS_TABLE_NAME)`.
              *   Create `Flag` Pydantic model instance (`flagId=uuid4()`, `userId=current_user.userId`, `status=FlagStatusEnum.OPEN`, etc.).
              *   Convert to dict (UUIDs to str), insert into DB. Return `Flag` model.
      *   **Step 6.1.5 (Add to `comment_service.py`):**
          *   Implement `async def get_comment_by_id(comment_id: CommentID, db_table: Optional[AstraDBCollection] = None) -> Optional[Comment]`: Fetches comment by `commentId`.
      *   **Step 6.1.6:** Create `app/api/v1/endpoints/moderation.py`:
          *   Import `APIRouter, Depends, HTTPException, status`. Models: `FlagCreateRequest, FlagResponse`. Dependencies: `get_current_viewer`, `get_current_moderator`. Services: `flag_service`.
          *   Initialize `router = APIRouter(prefix="/moderation", tags=["Moderation"])`.
          *   Implement `POST /flags` endpoint (generic flag, path is `/flags` as per API spec, so it might need its own router or careful prefixing if this router handles more `/moderation/*` paths. Let's assume a separate simple router for `/flags` or add to main `api_router_v1` directly to match `/flags` path).
          *   *Decision:* Add a new small router for `/flags` to keep paths clean as specified.
      *   **Step 6.1.6 (Revised):** Create `app/api/v1/endpoints/flags.py`:
          *   Import `APIRouter, Depends, status`. Models: `FlagCreateRequest, FlagResponse`. User model. Dependencies: `get_current_viewer`. Services: `flag_service`.
          *   Initialize `router = APIRouter(prefix="/flags", tags=["Flags"])`.
          *   Implement `POST /` endpoint:
              *   Decorator: `@router.post("/", response_model=FlagResponse, status_code=status.HTTP_201_CREATED, summary="Generic flag for video or comment")`.
              *   Protected by `current_user: Annotated[User, Depends(get_current_viewer)]`.
              *   Call `await flag_service.create_flag(request, current_user)`. Return result.
      *   **Step 6.1.7:** Modify `app/main.py`: Include `flags_router` (from `flags.py`) and `moderation_router` (from `moderation.py`, which will be populated next).
      *   **Step 6.1.8:** Tests:
          *   Models: `tests/models/test_flag.py`.
          *   Services: `tests/services/test_user_service.py` (for new role methods). `tests/services/test_comment_service.py` (for `get_comment_by_id`). `tests/services/test_flag_service.py` for `create_flag`.
          *   Endpoints: `tests/api/v1/endpoints/test_flags.py` for `POST /flags`. Test different content types, reasons, content not found.

  *   **Chunk 6.2: Moderator Flag Management (List, Details, Action)**
      *   **Step 6.2.1:** Modify `app/services/flag_service.py`:
          *   Implement `async def list_flags(page: int, page_size: int, status_filter: Optional[FlagStatusEnum] = None, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[Flag], int]`:
              *   Construct filter (include `status_filter` if provided). Paginate and sort (e.g., by `createdAt`). Return `List[Flag]` and total count.
          *   Implement `async def get_flag_by_id(flag_id: FlagID, db_table: Optional[AstraDBCollection] = None) -> Optional[Flag]`: Fetches flag by `flagId`.
          *   Implement `async def action_on_flag(flag: Flag, new_status: FlagStatusEnum, moderator_notes: Optional[str], moderator: User, db_table: Optional[AstraDBCollection] = None) -> Flag`:
              *   Updates `flag.status`, `flag.moderatorId`, `flag.moderatorNotes`, `flag.resolvedAt`, `flag.updatedAt`.
              *   Saves to DB.
              *   `# TODO: If flag.status is 'APPROVED', trigger action on content (e.g., soft-delete video/comment). This is complex and involves updating other services/tables. For now, just update flag status.`
              *   Returns updated `Flag`.
      *   **Step 6.2.2:** Modify `app/api/v1/endpoints/moderation.py`:
          *   Import `FlagResponse, FlagUpdateRequest, FlagStatusEnum, FlagID, Flag` from `app.models.flag`.
          *   Import `PaginatedResponse, Pagination` from `app.models.common`. `PaginationParams, common_pagination_params`.
          *   Implement `GET /flags` (Flag inbox for moderators):
              *   Path: `@router.get("/flags", response_model=PaginatedResponse[FlagResponse], summary="Flag inbox for moderators")`.
              *   Protected by `get_current_moderator`.
              *   Optional query param `status: Optional[FlagStatusEnum] = None`.
              *   Call `flag_service.list_flags`. Return `PaginatedResponse`.
          *   Implement `GET /flags/{flagId}` (Flag details):
              *   Path: `@router.get("/flags/{flag_id_path}", response_model=FlagResponse, summary="Flag details")`.
              *   Protected by `get_current_moderator`.
              *   Call `flag_service.get_flag_by_id`. If not found, 404. Return flag.
          *   Implement `POST /flags/{flagId}/action` (API spec, though PATCH might be more RESTful for status update, spec says POST):
              *   Path: `@router.post("/flags/{flag_id_path}/action", response_model=FlagResponse, summary="Act on a flag")`.
              *   Protected by `get_current_moderator`. Takes `action_request: FlagUpdateRequest`.
              *   Fetch flag using `flag_service.get_flag_by_id`. If not found or already resolved, 404/400.
              *   Call `flag_service.action_on_flag`. Return updated flag.
      *   **Step 6.2.3 (Specific flag endpoints on Video from API Spec Section 2):**
          *   These are `/videos/{videoId}/flags` (POST, GET) and `/videos/{videoId}/flags/{flagId}` (PATCH).
          *   POST `/videos/{videoId}/flags` is like the generic `/flags` but pre-filled `contentType` and `contentId`.
          *   GET `/videos/{videoId}/flags` lists flags for a specific video (moderator only).
          *   PATCH `/videos/{videoId}/flags/{flagId}` is like `/moderation/flags/{flagId}/action`.
          *   *Decision:* To avoid redundancy and keep moderation logic central, these video-specific flag routes can either be implemented in `video_catalog.py` calling `flag_service` methods, or the generic `/flags` and `/moderation/flags/...` routes can be preferred. The API spec is a bit duplicative here. Let's implement the generic ones first and then decide if specific wrappers are needed. For now, focus on `/moderation/flags/*`.
      *   **Step 6.2.4:** Tests:
          *   Services: `tests/services/test_flag_service.py` for `list_flags`, `get_flag_by_id`, `action_on_flag`.
          *   Endpoints: Create `tests/api/v1/endpoints/test_moderation.py`. Test the new moderator flag management endpoints. Test role protection.

  *   **Chunk 6.3: Moderator Role Management Endpoints**
      *   **Step 6.3.1:** Modify `app/api/v1/endpoints/moderation.py`:
          *   Import `UserID, User, UserProfile` from `app.models.user`.
          *   Import `user_service`.
          *   Implement `GET /users` (Search users for moderation purposes):
              *   Path: `@router.get("/users", response_model=List[UserProfile], summary="Search users (for moderator assignment)")`. (Response could be paginated if many users). For now, `List[UserProfile]`.
              *   Protected by `get_current_moderator`.
              *   Query param `search_query: Optional[str] = None`.
              *   Call a new `user_service.search_users(search_query)` (stub this service method to return a list of `User` objects, then map to `UserProfile`).
          *   Implement `POST /users/{userId}/assign-moderator`:
              *   Path: `@router.post("/users/{user_id_path}/assign-moderator", response_model=UserProfile, summary="Promote user to moderator")`.
              *   Protected by `get_current_moderator`.
              *   Call `user_service.get_user_by_id_from_table(user_id_path)`. If not found, 404.
              *   Call `user_service.assign_role_to_user(user_id_path, "moderator")`.
              *   Fetch updated user profile and return it.
          *   Implement `POST /users/{userId}/revoke-moderator`:
              *   Path: `@router.post("/users/{user_id_path}/revoke-moderator", response_model=UserProfile, summary="Demote user from moderator")`.
              *   Protected by `get_current_moderator`.
              *   Call `user_service.get_user_by_id_from_table(user_id_path)`. If not found, 404.
              *   Call `user_service.revoke_role_from_user(user_id_path, "moderator")`.
              *   Fetch updated user profile and return it.
      *   **Step 6.3.2 (Add to `user_service.py`):**
          *   Implement `async def search_users(query: Optional[str], db_table: Optional[AstraDBCollection] = None) -> List[User]`:
              *   If `query`, filter by email/firstName/lastName (using `$regex` or similar). If no `query`, list some users (e.g., recent, or first N).
              *   Map to `List[User]`.
      *   **Step 6.3.3:** Tests:
          *   Services: `tests/services/test_user_service.py` for `search_users`, `assign_role_to_user`, `revoke_role_from_user`.
          *   Endpoints: `tests/api/v1/endpoints/test_moderation.py` for the user role management endpoints.

  *   **Chunk 6.4: Content Action Stubs (Restore Soft-Deleted - Deferred full implementation)**
      *   **Step 6.4.1:** API Spec mentions `/moderation/videos/{videoId}/restore` and `/moderation/comments/{commentId}/restore`. This implies soft-deletion of content.
      *   Soft-deletion requires adding an `is_deleted: bool = False` and `deleted_at: Optional[datetime] = None` to `Video` and `Comment` models and DB schemas.
      *   Listing/getting videos/comments would then need to filter out `is_deleted == True` by default unless accessed by a moderator.
      *   The `action_on_flag` service would, if a flag is 'APPROVED' for removal, set `is_deleted = True` on the content.
      *   *Decision for this Epic:* This adds significant complexity across many existing parts. For Epic 6, we will:
          *   Add the `is_deleted`, `deleted_at` fields to `Video` and `Comment` Pydantic models.
          *   Add the stubbed RESTORE endpoints in `moderation.py`.
          *   The service methods for restore will simply log and return a success-like message.
          *   The actual logic of soft-deleting when a flag is actioned, and filtering deleted content, will be deferred to a follow-up "Content Lifecycle Management" epic or incorporated into a V1.1 refinement.
      *   **Step 6.4.2:** Modify `app/models/video.py` (`Video` model) and `app/models/comment.py` (`Comment` model): Add `is_deleted: bool = Field(False, exclude=True)` (exclude from default response unless specifically requested by moderator context), `deleted_at: Optional[datetime] = Field(None, exclude=True)`.
      *   **Step 6.4.3:** Modify `app/api/v1/endpoints/moderation.py`:
          *   Import `VideoID` from `app.models.video`, `CommentID` from `app.models.comment`.
          *   Define response models for restore if needed (e.g., a simple status message or the restored object). Let's use a simple status for now.
          *   `class RestoreResponse(BaseModel): id: Union[VideoID, CommentID]; status: str; message: str`.
          *   Implement `POST /videos/{videoId}/restore`:
              *   Protected by `get_current_moderator`.
              *   Call a new stubbed `video_service.restore_video(video_id)`.
              *   Return `RestoreResponse`.
          *   Implement `POST /comments/{commentId}/restore`:
              *   Protected by `get_current_moderator`.
              *   Call a new stubbed `comment_service.restore_comment(comment_id)`.
              *   Return `RestoreResponse`.
      *   **Step 6.4.4 (Add stubs to services):**
          *   In `video_service.py`: `async def restore_video(video_id: VideoID) -> bool: print(f"STUB: Restoring video {video_id}"); return True`.
          *   In `comment_service.py`: `async def restore_comment(comment_id: CommentID) -> bool: print(f"STUB: Restoring comment {comment_id}"); return True`.
      *   **Step 6.4.5:** Tests:
          *   Endpoints: In `tests/api/v1/endpoints/test_moderation.py`, add tests for the stubbed restore endpoints, checking for auth and basic success response.

---
This completes the plan for Epic 6. It's a large one. I'll now generate the LLM prompts.

## LLM Prompts - Iteration 6 (Epic 6: Moderation & Moderator Roles)

---
**Prompt 23 (was 6.1): Flag Models, Generic Flag Endpoint & Moderator Role Setup**
```text
Objective: Define models for content flagging, implement an endpoint for "viewers" to flag content, ensure "moderator" role concept in dependencies, and implement user service methods for role assignment/revocation.

Specifications:
1.  Create `app/models/flag.py`:
    *   Import `BaseModel, Field` from `pydantic`, `Optional, List, Union, Any` from `typing`, `UUID, uuid4` from `uuid`, `datetime` from `datetime`, `Enum` from `enum`.
    *   Import `VideoID` from `app.models.video`, `CommentID` from `app.models.comment`, `UserID` from `app.models.user` (or local UUID aliases with TODO to centralize).
    *   Define `FlagID = UUID`.
    *   Define `class ContentTypeEnum(str, Enum)`: `VIDEO = "video"`, `COMMENT = "comment"`.
    *   Define `class FlagReasonCodeEnum(str, Enum)`: `SPAM = "spam"`, `INAPPROPRIATE = "inappropriate"`, `HARASSMENT = "harassment"`, `COPYRIGHT = "copyright"`, `OTHER = "other"`.
    *   Define `class FlagStatusEnum(str, Enum)`: `OPEN = "open"`, `UNDER_REVIEW = "under_review"`, `APPROVED = "approved"`, `REJECTED = "rejected"`.
    *   Define `class FlagBase(BaseModel)`: `contentType: ContentTypeEnum`, `contentId: UUID` (Using plain UUID here; validation of which type it is will be in service), `reasonCode: FlagReasonCodeEnum`, `reasonText: Optional[str] = Field(None, max_length=500)`.
    *   Define `class FlagCreateRequest(FlagBase)`: (Pass).
    *   Define `class Flag(FlagBase)`: `flagId: FlagID`, `userId: UserID`, `createdAt: datetime`, `updatedAt: datetime`, `status: FlagStatusEnum = FlagStatusEnum.OPEN`, `moderatorId: Optional[UserID] = None`, `moderatorNotes: Optional[str] = None`, `resolvedAt: Optional[datetime] = None`.
    *   Define `class FlagResponse(Flag)`: (Pass).
    *   Define `class FlagUpdateRequest(BaseModel)`: `status: FlagStatusEnum`, `moderatorNotes: Optional[str] = Field(None, max_length=1000)`.
2.  Modify `app/api/v1/dependencies.py`:
    *   Verify `get_current_moderator` dependency is defined using `require_role(["moderator"])`. (From Prompt 8).
3.  Modify `app/services/user_service.py`:
    *   Import `AstraDBCollection`, `get_table`, `USERS_TABLE_NAME` (if not already global/accessible).
    *   Import `User` model.
    *   Implement `async def assign_role_to_user(user_to_modify_id: UUID, role_to_assign: str, db_table: Optional[AstraDBCollection] = None) -> Optional[User]`:
        *   If `db_table` is None, use `get_table(USERS_TABLE_NAME)`.
        *   Fetch user doc by `str(user_to_modify_id)`. If not found, return `None`.
        *   Get current roles (e.g., `current_roles = user_doc.get("roles", [])`).
        *   If `role_to_assign` not in `current_roles`, append it.
        *   Update user document in DB with new roles list.
        *   Refetch or update `user_doc` and return mapped `User` Pydantic model.
    *   Implement `async def revoke_role_from_user(user_to_modify_id: UUID, role_to_revoke: str, db_table: Optional[AstraDBCollection] = None) -> Optional[User]`:
        *   Fetch user doc. If not found, return `None`.
        *   Get current roles. If `role_to_revoke` in `current_roles`, remove it.
        *   Update user document. Return mapped `User` model.
4.  Create `app/services/flag_service.py`:
    *   Import models (`FlagCreateRequest`, `Flag`, `FlagID`, `ContentTypeEnum`, `FlagStatusEnum`, `FlagReasonCodeEnum`), `User`, DB utils (`get_table`, `AstraDBCollection`), `UUID, uuid4`, `datetime, timezone`, `Optional`.
    *   Import `video_service` from `app.services`, `comment_service` from `app.services`.
    *   Import `HTTPException, status` from `fastapi`.
    *   Import `VideoStatusEnum` from `app.models.video`.
    *   Define `FLAGS_TABLE_NAME: str = "flags"`.
    *   Implement `async def create_flag(request: FlagCreateRequest, current_user: User, db_table: Optional[AstraDBCollection] = None) -> Flag`:
        *   Content existence check:
            *   If `request.contentType == ContentTypeEnum.VIDEO`: `content = await video_service.get_video_by_id(request.contentId)`.
            *   Else if `request.contentType == ContentTypeEnum.COMMENT`: `content = await comment_service.get_comment_by_id(request.contentId)` (this service method will be added in next step).
            *   Else: `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type for flag")`.
            *   If not `content`: `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{request.contentType.value.capitalize()} not found")`.
        *   If `db_table` is None, `db_table = await get_table(FLAGS_TABLE_NAME)`.
        *   `now = datetime.now(timezone.utc)`.
        *   `new_flag_obj = Flag(flagId=uuid4(), userId=current_user.userId, contentType=request.contentType, contentId=request.contentId, reasonCode=request.reasonCode, reasonText=request.reasonText, createdAt=now, updatedAt=now, status=FlagStatusEnum.OPEN)`.
        *   Prepare doc for DB (UUIDs to str: `flagId`, `userId`, `contentId`).
        *   `await db_table.insert_one(...)`. Return `new_flag_obj`.
5.  Modify `app/services/comment_service.py`:
    *   Import `CommentID, Comment` from `app.models.comment`.
    *   Implement `async def get_comment_by_id(comment_id: CommentID, db_table: Optional[AstraDBCollection] = None) -> Optional[Comment]`:
        *   If `db_table` is None, `db_table = await get_table(COMMENTS_TABLE_NAME)`.
        *   Fetch comment doc by `str(comment_id)`. If found, map to `Comment` Pydantic model (convert UUIDs, datetimes) and return. Else `None`.
6.  Create `app/api/v1/endpoints/flags.py`:
    *   Import `APIRouter, Depends, status, HTTPException` from `fastapi`.
    *   Import `FlagCreateRequest, FlagResponse` from `app.models.flag`.
    *   Import `User` from `app.models.user`.
    *   Import `get_current_viewer` from `app.api.v1.dependencies`.
    *   Import `flag_service` from `app.services`.
    *   Import `Annotated` from `typing`.
    *   Initialize `router = APIRouter(prefix="/flags", tags=["Flags"])`.
    *   Implement `POST /` endpoint:
        *   Decorator: `@router.post("/", response_model=FlagResponse, status_code=status.HTTP_201_CREATED, summary="Flag content (video or comment)")`.
        *   Signature: `async def submit_flag(request: FlagCreateRequest, current_user: Annotated[User, Depends(get_current_viewer)])`.
        *   Call `new_flag = await flag_service.create_flag(request=request, current_user=current_user)`. Return `new_flag`.
7.  Create `app/api/v1/endpoints/moderation.py` (empty for now, just router setup):
    *   Import `APIRouter` from `fastapi`.
    *   Initialize `router = APIRouter(prefix="/moderation", tags=["Moderation Actions"])`.
8.  Modify `app/main.py`:
    *   Import `flags_router` from `flags.py` and `moderation_router` from `moderation.py`.
    *   Include both in `api_router_v1`.
9.  Create `tests/models/test_flag.py` (basic instantiation tests for enums and Flag model).
10. In `tests/services/test_user_service.py`: Add tests for `assign_role_to_user` and `revoke_role_from_user`.
11. In `tests/services/test_comment_service.py`: Add tests for `get_comment_by_id`.
12. Create `tests/services/test_flag_service.py`: Test `create_flag`. Mock content existence checks (`video_service.get_video_by_id`, `comment_service.get_comment_by_id`) and DB insert.
13. Create `tests/api/v1/endpoints/test_flags.py`: Test `POST /api/v1/flags/`. Mock `flag_service.create_flag`. Test different content types, valid/invalid content IDs (service raises 404). Auth.

Current Files to Work On:
*   `app/models/flag.py`
*   `app/api/v1/dependencies.py` (Verification)
*   `app/services/user_service.py`
*   `app/services/flag_service.py`
*   `app/services/comment_service.py`
*   `app/api/v1/endpoints/flags.py`
*   `app/api/v1/endpoints/moderation.py` (Initial setup)
*   `app/main.py`
*   `tests/models/test_flag.py`
*   `tests/services/test_user_service.py`
*   `tests/services/test_comment_service.py`
*   `tests/services/test_flag_service.py`
*   `tests/api/v1/endpoints/test_flags.py`

Provide the complete content for each new/modified file.
```---
**Prompt 24 (was 6.2): Moderator Flag Management (List, Details, Action)**
```text
Objective: Implement endpoints for moderators to list flags, view flag details, and act upon flags (approve/reject).

Specifications:
1.  Modify `app/services/flag_service.py`:
    *   Import `Flag, FlagID, FlagStatusEnum, User, Tuple, List, Optional, datetime, timezone`.
    *   Implement `async def list_flags(page: int, page_size: int, status_filter: Optional[FlagStatusEnum] = None, db_table: Optional[AstraDBCollection] = None) -> Tuple[List[Flag], int]`:
        *   If `db_table` is None, use `get_table(FLAGS_TABLE_NAME)`.
        *   `query_filter: Dict[str, Any] = {}`. If `status_filter`, add `{"status": status_filter.value}` to `query_filter`.
        *   `sort_options = {"createdAt": -1}`. `skip = (page - 1) * page_size`.
        *   Fetch docs using `find` with filter, skip, limit, sort.
        *   Fetch `total_items` using `count_documents` with filter.
        *   Map docs to `List[Flag]` (convert UUIDs, datetimes). Return `(flags_list, total_items)`.
    *   Implement `async def get_flag_by_id(flag_id: FlagID, db_table: Optional[AstraDBCollection] = None) -> Optional[Flag]`:
        *   Fetch flag doc by `str(flag_id)`. Map to `Flag` model if found.
    *   Implement `async def action_on_flag(flag_to_action: Flag, new_status: FlagStatusEnum, moderator_notes: Optional[str], moderator: User, db_table: Optional[AstraDBCollection] = None) -> Flag`:
        *   If `db_table` is None, use `get_table(FLAGS_TABLE_NAME)`.
        *   `now = datetime.now(timezone.utc)`.
        *   `update_payload = {"status": new_status.value, "moderatorId": str(moderator.userId), "moderatorNotes": moderator_notes, "resolvedAt": now, "updatedAt": now}`.
        *   Remove None values from `update_payload` before setting. E.g., `update_payload = {k: v for k, v in update_payload.items() if v is not None}`.
        *   `await db_table.update_one(filter={"flagId": str(flag_to_action.flagId)}, update={"$set": update_payload})`.
        *   `# TODO: If new_status is APPROVED, this is where logic to soft-delete/modify actual content would be triggered.`
        *   `# For now, just print a message for the TODO.`
        *   `if new_status == FlagStatusEnum.APPROVED: print(f"STUB: Flag {flag_to_action.flagId} approved. TODO: Trigger action on content {flag_to_action.contentType} ID {flag_to_action.contentId}.")`
        *   Return an updated `Flag` object: `return flag_to_action.model_copy(update=update_payload)`. (Pydantic v2 `model_copy`).
2.  Modify `app/api/v1/endpoints/moderation.py`:
    *   Import `FlagResponse, FlagUpdateRequest, FlagStatusEnum, FlagID, Flag` from `app.models.flag`.
    *   Import `PaginatedResponse, Pagination` from `app.models.common`.
    *   Import `PaginationParams, common_pagination_params, get_current_moderator` from `app.api.v1.dependencies`.
    *   Import `flag_service` from `app.services`.
    *   Import `List, Optional, Annotated` from `typing`. User model.
    *   Implement `GET /flags` endpoint:
        *   Decorator: `@router.get("/flags", response_model=PaginatedResponse[FlagResponse], summary="List all flags (moderator inbox)")`.
        *   Signature: `async def list_all_flags(pagination: Annotated[PaginationParams, Depends(common_pagination_params)], status: Annotated[Optional[FlagStatusEnum], Query(description="Filter flags by status")] = None, current_moderator: Annotated[User, Depends(get_current_moderator)] = None)`.
        *   Call `flags_list, total = await flag_service.list_flags(page=pagination.page, page_size=pagination.pageSize, status_filter=status)`.
        *   Construct and return `PaginatedResponse`.
    *   Implement `GET /flags/{flag_id_path}` endpoint:
        *   Decorator: `@router.get("/flags/{flag_id_path}", response_model=FlagResponse, summary="Get details of a specific flag")`.
        *   Signature: `async def get_specific_flag_details(flag_id_path: FlagID, current_moderator: Annotated[User, Depends(get_current_moderator)])`.
        *   Call `flag = await flag_service.get_flag_by_id(flag_id=flag_id_path)`.
        *   If not `flag`, raise `HTTPException(status.HTTP_404_NOT_FOUND, "Flag not found")`.
        *   Return `flag`.
    *   Implement `POST /flags/{flag_id_path}/action` endpoint:
        *   Decorator: `@router.post("/flags/{flag_id_path}/action", response_model=FlagResponse, summary="Take action on a specific flag")`.
        *   Signature: `async def action_flag(flag_id_path: FlagID, action_request: FlagUpdateRequest, current_moderator: Annotated[User, Depends(get_current_moderator)])`.
        *   Fetch `flag_to_action = await flag_service.get_flag_by_id(flag_id=flag_id_path)`.
        *   If not `flag_to_action`, raise `HTTPException(status.HTTP_404_NOT_FOUND, "Flag not found")`.
        *   If `flag_to_action.status not in [FlagStatusEnum.OPEN, FlagStatusEnum.UNDER_REVIEW]`: raise `HTTPException(status.HTTP_400_BAD_REQUEST, "Flag has already been resolved")`.
        *   Call `updated_flag = await flag_service.action_on_flag(flag_to_action=flag_to_action, new_status=action_request.status, moderator_notes=action_request.moderatorNotes, moderator=current_moderator)`.
        *   Return `updated_flag`.
3.  In `tests/services/test_flag_service.py`:
    *   Add unit tests for `list_flags`, `get_flag_by_id`, and `action_on_flag`.
    *   Mock DB calls. Test filtering, pagination, status updates, and the TODO print message.
4.  Create `tests/api/v1/endpoints/test_moderation.py`:
    *   Import `AsyncClient`, `status`, relevant models.
    *   Write integration tests for the new `/moderation/flags` GET (list), `/moderation/flags/{flagId}` GET (details), and `/moderation/flags/{flagId}/action` POST endpoints.
    *   Mock `flag_service` methods.
    *   Use helper to get JWT for "moderator" and "viewer" (for auth failure tests).
    *   Test successful operations, flag not found, flag already resolved, invalid status transitions.

Current Files to Work On:
*   `app/services/flag_service.py`
*   `app/api/v1/endpoints/moderation.py`
*   `tests/services/test_flag_service.py`
*   `tests/api/v1/endpoints/test_moderation.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 25 (was 6.3): Moderator Role Management Endpoints**
```text
Objective: Implement endpoints for moderators to search users and assign/revoke the "moderator" role to/from other users.

Specifications:
1.  Modify `app/services/user_service.py`:
    *   Import `User, UserProfile` from `app.models.user`.
    *   Import `List, Optional, Dict, Any`.
    *   Implement `async def search_users(query: Optional[str], db_table: Optional[AstraDBCollection] = None) -> List[User]`:
        *   If `db_table` is None, use `get_table(USERS_TABLE_NAME)`.
        *   `query_filter: Dict[str, Any] = {}`.
        *   If `query`:
            *   `escaped_query = re.escape(query)`.
            *   `query_filter["$or"] = [{"email": {"$regex": escaped_query, "$options": "i"}}, {"firstName": {"$regex": escaped_query, "$options": "i"}}, {"lastName": {"$regex": escaped_query, "$options": "i"}}]`. (Need `import re`).
        *   Fetch user docs using `find(filter=query_filter, limit=20)` (limit results for now).
        *   Map docs to `List[User]` (convert UUIDs, etc.). Return the list.
    *   Ensure `assign_role_to_user` and `revoke_role_from_user` (from Prompt 23) correctly fetch the user document, modify the `roles` list (stored as a list of strings in DB), update the document, and return the updated `User` Pydantic model.
2.  Modify `app/api/v1/endpoints/moderation.py`:
    *   Import `UserID, User, UserProfile` from `app/models.user`. (Ensure `UserProfile` matches the response for user details; `User` model might be sufficient if it contains all needed fields like `userId`, `firstName`, `lastName`, `email`, `roles`). Let's use `User` as the response model for simplicity, assuming it contains what `UserProfile` would.
    *   Import `user_service` from `app.services`.
    *   Import `List, Optional, Annotated`.
    *   Implement `GET /users` endpoint:
        *   Decorator: `@router.get("/users", response_model=List[User], summary="Search for users to manage roles")`.
        *   Signature: `async def find_users_for_moderation(search_query: Annotated[Optional[str], Query(None, description="Search by email, first name, or last name")] = None, current_moderator: Annotated[User, Depends(get_current_moderator)] = None)`.
        *   Call `users_list = await user_service.search_users(query=search_query)`.
        *   Return `users_list`.
    *   Implement `POST /users/{user_id_path}/assign-moderator` endpoint:
        *   Decorator: `@router.post("/users/{user_id_path}/assign-moderator", response_model=User, summary="Assign moderator role to a user")`.
        *   Signature: `async def assign_moderator_role(user_id_path: UserID, current_moderator: Annotated[User, Depends(get_current_moderator)])`.
        *   Call `updated_user = await user_service.assign_role_to_user(user_to_modify_id=user_id_path, role_to_assign="moderator")`.
        *   If not `updated_user`, raise `HTTPException(status.HTTP_404_NOT_FOUND, "User not found")`.
        *   Return `updated_user`.
    *   Implement `POST /users/{user_id_path}/revoke-moderator` endpoint:
        *   Decorator: `@router.post("/users/{user_id_path}/revoke-moderator", response_model=User, summary="Revoke moderator role from a user")`.
        *   Signature: `async def revoke_moderator_role(user_id_path: UserID, current_moderator: Annotated[User, Depends(get_current_moderator)])`.
        *   Call `updated_user = await user_service.revoke_role_from_user(user_to_modify_id=user_id_path, role_to_revoke="moderator")`.
        *   If not `updated_user` (e.g., user not found or role wasn't assigned), raise `HTTPException(status.HTTP_404_NOT_FOUND, "User not found or role not present to revoke")`. (Service should clarify return for "role not present").
        *   Return `updated_user`.
3.  In `tests/services/test_user_service.py`:
    *   Add unit tests for `search_users`. Mock DB calls. Test with and without query.
    *   Refine tests for `assign_role_to_user` and `revoke_role_from_user`: ensure they correctly modify the roles list and return the updated `User` model. Test edge cases like role already present/absent, user not found.
4.  In `tests/api/v1/endpoints/test_moderation.py`:
    *   Add integration tests for `GET /moderation/users`, `POST /moderation/users/{userId}/assign-moderator`, and `POST /moderation/users/{userId}/revoke-moderator`.
    *   Mock `user_service` methods.
    *   Use JWT for "moderator" and test auth.
    *   Test user not found scenarios, successful role changes.

Current Files to Work On:
*   `app/services/user_service.py`
*   `app/api/v1/endpoints/moderation.py`
*   `tests/services/test_user_service.py`
*   `tests/api/v1/endpoints/test_moderation.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 26 (was 6.4): Content Action Stubs (Restore Soft-Deleted)**
```text
Objective: Add stubbed endpoints for moderators to restore "soft-deleted" videos and comments. This involves adding `is_deleted` fields to models but deferring the actual soft-delete and filtering logic.

Specifications:
1.  Modify `app/models/video.py`:
    *   In the `Video` model, add:
        *   `is_deleted: bool = Field(False, description="Whether the video is soft-deleted")`
        *   `deleted_at: Optional[datetime] = Field(None, description="Timestamp of soft-deletion")`
    *   Consider if these fields should be excluded from default serialization in `VideoDetailResponse` / `VideoSummary` unless a specific moderator context is active. For now, include them, and filtering can happen at the client or API gateway if needed, or refine Pydantic response models later.
2.  Modify `app/models/comment.py`:
    *   In the `Comment` model, add:
        *   `is_deleted: bool = Field(False, description="Whether the comment is soft-deleted")`
        *   `deleted_at: Optional[datetime] = Field(None, description="Timestamp of soft-deletion")`
3.  Modify `app/api/v1/endpoints/moderation.py`:
    *   Import `VideoID` from `app.models.video`, `CommentID` from `app/models.comment`.
    *   Import `Union` from `typing`. (If not already present for `BaseModel`).
    *   Import `BaseModel` from `pydantic`. (If not already present).
    *   Define `class ContentRestoreResponse(BaseModel)`: `content_id: UUID # Store as generic UUID, actual type known by context`, `content_type: str`, `status_message: str`.
    *   Implement `POST /videos/{video_id_path}/restore` endpoint:
        *   Decorator: `@router.post("/videos/{video_id_path}/restore", response_model=ContentRestoreResponse, summary="Restore a soft-deleted video (STUBBED)")`.
        *   Signature: `async def restore_video_content(video_id_path: VideoID, current_moderator: Annotated[User, Depends(get_current_moderator)])`.
        *   Call `success = await video_service.restore_video(video_id=video_id_path) # STUBBED service method`.
        *   If `success`: `message = f"Video {video_id_path} restore process initiated (stub)."` else: `message = f"Failed to initiate restore for video {video_id_path} (stub). Possible video not found or not deleted."`
        *   Return `ContentRestoreResponse(content_id=video_id_path, content_type="video", status_message=message)`.
    *   Implement `POST /comments/{comment_id_path}/restore` endpoint:
        *   Decorator: `@router.post("/comments/{comment_id_path}/restore", response_model=ContentRestoreResponse, summary="Restore a soft-deleted comment (STUBBED)")`.
        *   Signature: `async def restore_comment_content(comment_id_path: CommentID, current_moderator: Annotated[User, Depends(get_current_moderator)])`.
        *   Call `success = await comment_service.restore_comment(comment_id=comment_id_path) # STUBBED service method`.
        *   Construct and return `ContentRestoreResponse` similarly.
4.  Modify `app/services/video_service.py`:
    *   Add stubbed `async def restore_video(video_id: VideoID) -> bool`:
        *   `# TODO: Implement logic to find video, set is_deleted=False, deleted_at=None.`
        *   `# For now, check if video exists for a slightly more realistic stub.`
        *   `video = await get_video_by_id(video_id) # Uses existing method`
        *   `if not video: print(f"STUB: Video {video_id} not found for restore."); return False`
        *   `print(f"STUB: Video {video_id} marked for restoration. Current is_deleted: {getattr(video, 'is_deleted', 'N/A')}")`.
        *   `return True # Simulate success`.
5.  Modify `app/services/comment_service.py`:
    *   Add stubbed `async def restore_comment(comment_id: CommentID) -> bool`:
        *   `# TODO: Implement logic to find comment, set is_deleted=False, deleted_at=None.`
        *   `comment = await get_comment_by_id(comment_id)`
        *   `if not comment: print(f"STUB: Comment {comment_id} not found for restore."); return False`
        *   `print(f"STUB: Comment {comment_id} marked for restoration. Current is_deleted: {getattr(comment, 'is_deleted', 'N/A')}")`.
        *   `return True # Simulate success`.
6.  In `tests/api/v1/endpoints/test_moderation.py`:
    *   Add integration tests for the stubbed `POST /moderation/videos/{videoId}/restore` and `POST /moderation/comments/{commentId}/restore` endpoints.
    *   Mock the new stubbed service methods (`video_service.restore_video`, `comment_service.restore_comment`).
    *   Test authentication with moderator token.
    *   Verify the basic success response structure.
    *   Test scenario where service mock returns `False` (e.g. content not found by stub).

Current Files to Work On:
*   `app/models/video.py`
*   `app/models/comment.py`
*   `app/api/v1/endpoints/moderation.py`
*   `app/services/video_service.py`
*   `app/services/comment_service.py`
*   `tests/api/v1/endpoints/test_moderation.py`

Provide the complete content for each new/modified file. The actual soft-delete logic in services (when a flag is 'APPROVED') and filtering of soft-deleted content from general listings are deferred.
```