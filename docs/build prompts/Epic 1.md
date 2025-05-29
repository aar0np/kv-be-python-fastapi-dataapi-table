## Project Blueprint: KillrVideo 2025 Python Backend

**Overall Goal:** Implement the KillrVideo 2025 Python backend using FastAPI, AstraDB (via `astrapy` with Table API), and Poetry, following best practices and the provided specifications. The output will be a monorepo structure suitable for deploying individual services.

---

**Phase 0: Project Foundation & Core Setup**
*Goal: Establish a working FastAPI project with configuration, database connectivity, and basic Pydantic models.*

  *   **Chunk 0.1: Project Initialization & Basic Structure**
      *   **Step 0.1.1:** Initialize Poetry project. Add core production dependencies: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `astrapy`. Add core development dependencies: `pytest`, `pytest-asyncio`, `httpx`, `mypy`, `ruff`.
      *   **Step 0.1.2:** Create initial directory structure as per Build Spec v1.1: `app/`, `app/core/`, `app/models/`, `app/api/v1/endpoints/`, `tests/`, `tests/api/v1/endpoints`. Add `__init__.py` files where necessary.
      *   **Step 0.1.3:** Implement `app/main.py`: Create FastAPI app instance. Add a root GET `/` health check endpoint that returns a simple JSON message.
      *   **Step 0.1.4:** Implement `app/core/config.py`: Define `Settings` class using Pydantic-Settings. Include initial settings: `PROJECT_NAME`, `API_V1_STR`. Load from a `.env` file. Create `.env.example`.
      *   **Step 0.1.5:** Tests:
          *   Write a test for the root `/` endpoint in `tests/test_main.py`.
          *   Write a test for configuration loading in `tests/core/test_config.py` (ensure settings are loaded).

  *   **Chunk 0.2: Database Client & Core Error/Response Models**
      *   **Step 0.2.1:** Update `app/core/config.py`: Add AstraDB settings: `ASTRA_DB_API_ENDPOINT`, `ASTRA_DB_APPLICATION_TOKEN`, `ASTRA_DB_KEYSPACE`. Update `.env.example`.
      *   **Step 0.2.2:** Implement `app/db/astra_client.py`:
          *   `init_astra_db()`: Initializes `AstraDB` client.
          *   `get_astra_db()`: Returns the initialized client.
          *   `get_table(table_name: str)`: Returns an `AstraDBCollection` for the given table name.
          *   Add logging for initialization.
      *   **Step 0.2.3:** Modify `app/main.py`: Add a startup event handler to call `init_astra_db()`.
      *   **Step 0.2.4:** Implement `app/models/common.py`: Define `ProblemDetail`, `Pagination`, `PaginatedResponse[DataT]`.
      *   **Step 0.2.5:** Modify `app/main.py`: Implement global exception handlers for `HTTPException` and generic `Exception` that return responses using the `ProblemDetail` model.
      *   **Step 0.2.6:** Tests:
          *   Write tests for `astra_client.py` in `tests/db/test_astra_client.py` (mock `AstraDB` calls to test initialization logic and `get_table`).
          *   Write tests for the global exception handlers in `tests/test_main.py` (trigger exceptions and verify `ProblemDetail` response).

---

**Phase 1: Epic 1 - Account Management**
*Goal: Implement user registration, login, profile management, and foundational authentication/authorization.*

  *   **Chunk 1.1: User Models & Registration Endpoint (Schema & API Definition)**
      *   **Step 1.1.1:** Implement `app/models/user.py`: Define `UserBase`, `UserCreateRequest`, `UserCreateResponse` (with `userId: UUID`), and `User` (initially with `userId`, `firstName`, `lastName`, `email`, and `roles: List[str]`).
      *   **Step 1.1.2:** Create `app/api/v1/endpoints/account_management.py`: Initialize an `APIRouter` with tags=["Users"].
      *   **Step 1.1.3:** In `account_management.py`, implement the `POST /users/register` endpoint:
          *   Takes `UserCreateRequest` as input.
          *   Returns `UserCreateResponse` with status `201 Created`.
          *   For now, this endpoint will be a stub: validate input, generate a dummy `userId`, and return a mock response (no DB interaction yet).
      *   **Step 1.1.4:** In `app/main.py` (or a service-specific entrypoint like `app/main_account.py` if preferred for early structuring), include the `account_management.router`. For simplicity in early stages, using `app/main.py` is fine.
      *   **Step 1.1.5:** Tests:
          *   Write tests in `tests/api/v1/endpoints/test_account_management.py` for `POST /users/register`:
              *   Test successful registration (mocked response).
              *   Test request validation errors (e.g., missing fields, invalid email).

  *   **Chunk 1.2: Password Hashing & User Service (Registration with DB)**
      *   **Step 1.2.1:** Implement `app/core/security.py`: Add `pwd_context` (using bcrypt), `verify_password(plain, hashed)`, and `get_password_hash(password)`.
      *   **Step 1.2.2:** Create `app/services/user_service.py`.
      *   **Step 1.2.3:** In `user_service.py`, implement `create_user_in_table(user_in: UserCreateRequest) -> Dict[str, Any]`:
          *   Uses `get_table(USERS_TABLE)` (define `USERS_TABLE = "users"` in `astra_client.py` or `user_service.py`).
          *   Hashes the password using `get_password_hash`.
          *   Constructs a user document (dictionary) including `userid` (generate `uuid4`), `hashed_password`, default `roles=["viewer"]`, `created_at`.
          *   Calls `users_table.insert_one(document)`.
          *   Returns the created user document.
      *   **Step 1.2.4:** In `user_service.py`, implement `get_user_by_email_from_table(email: str) -> Optional[Dict[str, Any]]`:
          *   Uses `get_table(USERS_TABLE)`.
          *   Calls `users_table.find_one(filter={"email": email})`.
      *   **Step 1.2.5:** Update `POST /users/register` endpoint in `account_management.py`:
          *   Call `user_service.get_user_by_email_from_table` to check if user exists. Raise `HTTPException 400` if email is already registered.
          *   Call `user_service.create_user_in_table`.
          *   Map the result from the service to `UserCreateResponse`.
      *   **Step 1.2.6:** Tests:
          *   Write unit tests for `app/core/security.py` password functions.
          *   Write unit tests in `tests/services/test_user_service.py` for `create_user_in_table` and `get_user_by_email_from_table` (mock `get_table` and its `AstraDBCollection` methods).
          *   Update integration tests for `POST /users/register` to mock `user_service` calls and verify interactions, including "email already registered" scenario.

  *   **Chunk 1.3: JWT & Login Endpoint**
      *   **Step 1.3.1:** Update `app/core/config.py`: Add JWT settings: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`. Update `.env.example`.
      *   **Step 1.3.2:** In `app/core/security.py`:
          *   Define `TokenPayload(BaseModel)` with `sub: Optional[str] = None`, `roles: List[str] = []`, `exp: Optional[datetime] = None`.
          *   Implement `create_access_token(subject: Union[str, Any], roles: List[str], expires_delta: Optional[timedelta] = None) -> str`.
      *   **Step 1.3.3:** In `app/models/user.py`: Define `UserLoginRequest` and `UserLoginResponse` (containing `token: str` and `user: User`).
      *   **Step 1.3.4:** In `user_service.py`, implement `authenticate_user_from_table(email: str, password: str) -> Optional[User]`:
          *   Uses `get_user_by_email_from_table`.
          *   Uses `verify_password`.
          *   If authentication is successful, maps the user data dictionary from DB to the `User` Pydantic model and returns it.
      *   **Step 1.3.5:** In `account_management.py`, implement `POST /users/login` endpoint:
          *   Takes `UserLoginRequest` (FastAPI will parse this from form data if you use `OAuth2PasswordRequestForm`, or from JSON body if you define `UserLoginRequest` for JSON). Per OpenAPI, it's JSON.
          *   Calls `user_service.authenticate_user_from_table`. Raise `HTTPException 401` if authentication fails.
          *   If successful, creates JWT using `create_access_token` (subject=user.userId, roles=user.roles).
          *   Returns `UserLoginResponse`.
      *   **Step 1.3.6:** Tests:
          *   Write unit tests for `create_access_token` in `app/core/security.py`.
          *   Write unit tests for `user_service.authenticate_user_from_table` (mock DB calls).
          *   Write integration tests for `POST /users/login` (mock `user_service` calls), testing successful login and authentication failure.

  *   **Chunk 1.4: Protected Route - Get User Profile**
      *   **Step 1.4.1:** Create `app/api/v1/dependencies.py`. Implement `reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/users/login")`.
      *   **Step 1.4.2:** In `dependencies.py`, implement `get_current_user_token_payload(token: Annotated[str, Depends(reusable_oauth2)]) -> TokenPayload`: Decodes JWT, checks expiry, handles `JWTError`, `ValidationError`.
      *   **Step 1.4.3:** In `user_service.py`, implement `get_user_by_id_from_table(user_id: UUID) -> Optional[User]`: Fetches user by `userid` from table and maps to `User` model.
      *   **Step 1.4.4:** In `dependencies.py`, implement `get_current_user_from_token(payload: Annotated[TokenPayload, Depends(get_current_user_token_payload)]) -> User`:
          *   Uses `user_service.get_user_by_id_from_table` with `payload.sub` (user ID).
          *   Raises `HTTPException 401` or `404` if user not found or token invalid.
          *   Returns the `User` Pydantic model.
      *   **Step 1.4.5:** In `app/models/user.py`, define `UserProfile(UserBase)` (or similar, based on what profile info is public). `User` model itself can be used if its fields are appropriate for profile response.
      *   **Step 1.4.6:** In `account_management.py`, implement `GET /users/me` endpoint:
          *   Protected by `Depends(get_current_user_from_token)`.
          *   Returns the current `User` object (or `UserProfile` mapping).
      *   **Step 1.4.7:** Tests:
          *   Write unit tests for `dependencies.py` functions (`get_current_user_token_payload`, `get_current_user_from_token`), mocking service calls and JWT functions.
          *   Write integration tests for `GET /users/me`:
              *   Test with a valid token.
              *   Test with an invalid/expired token.
              *   Test with no token.

  *   **Chunk 1.5: Update User Profile**
      *   **Step 1.5.1:** In `app/models/user.py`, define `UserProfileUpdateRequest(BaseModel)` with optional fields (e.g., `firstName: Optional[str]`, `lastName: Optional[str]`).
      *   **Step 1.5.2:** In `user_service.py`, implement `update_user_in_table(user_id: UUID, update_data: UserProfileUpdateRequest) -> Optional[User]`:
          *   Fetches the user by `user_id`.
          *   Updates the user document in the DB with non-None fields from `update_data`. Uses `users_table.update_one()`.
          *   Returns the updated `User` model. (Handle case where user not found).
      *   **Step 1.5.3:** In `account_management.py`, implement `PUT /users/me` endpoint:
          *   Protected by `Depends(get_current_user_from_token)`.
          *   Takes `UserProfileUpdateRequest` as input.
          *   Calls `user_service.update_user_in_table`.
          *   Returns the updated `User` (or `UserProfile`).
      *   **Step 1.5.4:** Tests:
          *   Write unit tests for `user_service.update_user_in_table` (mock DB calls).
          *   Write integration tests for `PUT /users/me`, testing successful update and scenarios like user not found (though auth would catch this first).

  *   **Chunk 1.6: Role-Based Access Control (RBAC) Foundation**
      *   **Step 1.6.1:** Update `app/core/security.py`: `TokenPayload` already has `roles`. `create_access_token` already accepts `roles`.
      *   **Step 1.6.2:** Update `app/models/user.py`: `User` model already has `roles: List[str]`.
      *   **Step 1.6.3:** Ensure `user_service.create_user_in_table` assigns a default role (e.g., `["viewer"]`) and stores it in the DB. Ensure `authenticate_user_from_table` and `get_user_by_id_from_table` correctly load roles into the `User` model.
      *   **Step 1.6.4:** In `app/api/v1/dependencies.py`, implement `require_role(required_roles: List[str])` dependency factory that takes `current_user: User = Depends(get_current_user_from_token)`. Checks if user has ANY of the `required_roles`. Raises `HTTPException 403` if not.
      *   **Step 1.6.5:** In `dependencies.py`, define `get_current_viewer: User = Depends(require_role(["viewer", "creator", "moderator"]))`. (Initially, only "viewer" exists).
      *   **Step 1.6.6:** Update `GET /users/me` and `PUT /users/me` to use `current_user: User = Depends(get_current_viewer)` instead of `Depends(get_current_user_from_token)` directly, to test the RBAC flow.
      *   **Step 1.6.7:** Tests:
          *   Write unit tests for `dependencies.require_role`.
          *   Update integration tests for `/users/me` to ensure they still work with `get_current_viewer` and that a user with the "viewer" role can access them.
          *   (Later epics will add routes requiring "creator" or "moderator" to test those paths).

---
This completes the detailed plan and breakdown for Phase 0 and Epic 1. I will now proceed to generate the LLM prompts for this initial set.

## LLM Prompts - Iteration 1 (Phase 0 & Epic 1: Account Management)

Each prompt will assume the LLM has context of the previous prompts and the overall project goal. The "Current Files to Work On" section indicates primary focus, but the LLM might need to touch related files for imports, etc.

---
**Prompt 1: Project Initialization & Basic FastAPI App**
```text
Objective: Initialize the KillrVideo Python backend project using Poetry and set up a basic FastAPI application with a health check endpoint and initial configuration.

Specifications:
1.  Create a new Python project named `killrvideo-python-backend` using `poetry init`.
    *   Python version: `^3.10`
    *   Add basic metadata (description, author - you can use placeholders).
2.  Add the following production dependencies using `poetry add`:
    *   `fastapi`
    *   `uvicorn[standard]`
    *   `pydantic-settings`
    *   `python-jose[cryptography]`
    *   `passlib[bcrypt]`
    *   `astrapy`
3.  Add the following development dependencies using `poetry add --group dev`:
    *   `pytest`
    *   `pytest-asyncio`
    *   `httpx`
    *   `mypy`
    *   `ruff`
4.  Create the initial directory structure:
    *   `app/`
    *   `app/core/`
    *   `app/models/`
    *   `app/api/`
    *   `app/api/v1/`
    *   `app/api/v1/endpoints/`
    *   `tests/`
    *   `tests/core/` (if you plan tests for core components immediately)
    *   `tests/api/`
    *   `tests/api/v1/`
    *   `tests/api/v1/endpoints/`
    *   Add `__init__.py` files to all new Python package directories (`app`, `app/core`, `app/models`, `app/api`, `app/api/v1`, `app/api/v1/endpoints`, `tests`, etc.) to make them importable.
5.  In `app/core/config.py`:
    *   Create a `Settings` class inheriting from `pydantic_settings.BaseSettings`.
    *   Add initial settings: `PROJECT_NAME: str = "KillrVideo 2025 Python Backend"` and `API_V1_STR: str = "/api/v1"`.
    *   Configure it to load from a `.env` file (using `class Config: env_file = ".env"`).
    *   Instantiate `settings = Settings()`.
6.  Create a `.env.example` file in the project root with placeholders for future environment variables (for now, it can be empty or just have `PROJECT_NAME` if you want to test overriding it). Add `.env` to `.gitignore`.
7.  In `app/main.py`:
    *   Import `FastAPI` and `settings` from `app.core.config`.
    *   Create a FastAPI app instance: `app = FastAPI(title=settings.PROJECT_NAME)`.
    *   Implement a root `GET /` health check endpoint that returns `{"message": f"Welcome to {settings.PROJECT_NAME}!"}`.
8.  In `tests/test_main.py`:
    *   Write an asynchronous test using `httpx.AsyncClient` for the `GET /` endpoint.
    *   Assert the status code is `200 OK`.
    *   Assert the response JSON matches the expected message.
9.  In `tests/core/test_config.py`:
    *   Write a test to ensure `settings.PROJECT_NAME` is loaded correctly. You can temporarily create a `.env` file for the test or mock environment variables if preferred.

Current Files to Work On:
*   `pyproject.toml` (implicitly by Poetry commands)
*   `app/main.py`
*   `app/core/config.py`
*   `.env.example`
*   `.gitignore`
*   `tests/test_main.py`
*   `tests/core/test_config.py`
*   Various `__init__.py` files.

Provide the complete content for each new/modified file.
```
---
**Prompt 2: Database Client, Core Error/Response Models & Startup Event**
```text
Objective: Implement AstraDB client setup, define core Pydantic models for error and paginated responses, and integrate DB initialization into the FastAPI app lifecycle with global exception handlers.

Specifications:
1.  Update `app/core/config.py`:
    *   Add AstraDB settings to the `Settings` class: `ASTRA_DB_API_ENDPOINT: str`, `ASTRA_DB_APPLICATION_TOKEN: str`, `ASTRA_DB_KEYSPACE: str`.
    *   Ensure these are loaded from environment variables.
2.  Update `.env.example`: Add placeholders for `ASTRA_DB_API_ENDPOINT`, `ASTRA_DB_APPLICATION_TOKEN`, `ASTRA_DB_KEYSPACE`.
3.  Create `app/db/astra_client.py`:
    *   Import `Optional, logging`, `AstraDB, AstraDBCollection` from `astrapy.db`, and `settings` from `app.core.config`.
    *   Initialize `logger = logging.getLogger(__name__)` and `db_instance: Optional[AstraDB] = None`.
    *   Implement `async def init_astra_db()`:
        *   Checks if required AstraDB settings are present in `settings`. Logs an error and raises `ValueError` if not.
        *   Initializes the global `db_instance` with `AstraDB(...)`, using `settings.ASTRA_DB_KEYSPACE` for the `namespace` parameter.
        *   Logs successful initialization or connection errors.
    *   Implement `async def get_astra_db() -> AstraDB`: Returns `db_instance`. Raises `RuntimeError` if not initialized. Should call `init_astra_db` if `db_instance` is None.
    *   Implement `async def get_table(table_name: str) -> AstraDBCollection`: Gets `db` from `get_astra_db()` and returns `db.collection(table_name)`.
4.  Modify `app/main.py`:
    *   Import `init_astra_db` from `app.db.astra_client`.
    *   Add an application startup event handler: `@app.on_event("startup") async def startup_event(): await init_astra_db()`.
5.  Create `app/models/common.py`:
    *   Import `BaseModel, Field` from `pydantic`, and `List, TypeVar, Generic, Optional, Union` from `typing`.
    *   Define `DataT = TypeVar('DataT')`.
    *   Define `class ProblemDetail(BaseModel)`: `type: str = "about:blank"`, `title: str`, `status: int`, `detail: Optional[str] = None`, `instance: Optional[str] = None`.
    *   Define `class Pagination(BaseModel)`: `currentPage: int`, `pageSize: int`, `totalItems: int`, `totalPages: int`.
    *   Define `class PaginatedResponse(BaseModel, Generic[DataT])`: `data: List[DataT]`, `pagination: Pagination`.
6.  Modify `app/main.py`:
    *   Import `HTTPException, Request, status, JSONResponse` from `fastapi` and `ProblemDetail` from `app.models.common`. Also import `HTTPStatus` from `http`.
    *   Implement a global exception handler for `HTTPException`: `@app.exception_handler(HTTPException) async def http_exception_handler(request: Request, exc: HTTPException)`. It should return a `JSONResponse` with content from `ProblemDetail`, populating fields from `exc` and `request.url`.
    *   Implement a global exception handler for generic `Exception`: `@app.exception_handler(Exception) async def generic_exception_handler(request: Request, exc: Exception)`. It should log the error (e.g., `logger.error("Unhandled exception:", exc_info=True)`) and return a `JSONResponse` with a generic `ProblemDetail` for status 500. (You'll need to import `logging` and get a logger instance in `main.py` for this).
7.  In `tests/db/test_astra_client.py`:
    *   Write unit tests for `init_astra_db`, `get_astra_db`, `get_table`.
    *   Use `unittest.mock.patch` to mock `AstraDB` from `astrapy.db` to avoid actual DB calls.
    *   Test scenarios: successful initialization, missing config, `get_astra_db` before/after init.
8.  In `tests/test_main.py`:
    *   Add tests for the global exception handlers:
        *   Create a temporary route that raises an `HTTPException` and verify the `ProblemDetail` response structure and status code.
        *   Create a temporary route that raises a generic `Exception` and verify the `ProblemDetail` response for status 500.

Current Files to Work On:
*   `app/core/config.py`
*   `.env.example`
*   `app/db/astra_client.py`
*   `app/main.py`
*   `app/models/common.py`
*   `tests/db/test_astra_client.py`
*   `tests/test_main.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 3: User Models & Stubbed Registration Endpoint**
```text
Objective: Define Pydantic models for User entities and implement a stubbed version of the user registration endpoint. This step focuses on API contract and request/response validation.

Specifications:
1.  Create `app/models/user.py`:
    *   Import `BaseModel, EmailStr, Field` from `pydantic`, `List, Optional` from `typing`, and `UUID, uuid4` from `uuid`.
    *   Define `class UserBase(BaseModel)`: `firstName: str = Field(..., min_length=1, max_length=50)`, `lastName: str = Field(..., min_length=1, max_length=50)`, `email: EmailStr`.
    *   Define `class UserCreateRequest(UserBase)`: `password: str = Field(..., min_length=8)`.
    *   Define `class UserCreateResponse(UserBase)`: `userId: UUID`.
    *   Define `class User(UserBase)`: `userId: UUID`, `roles: List[str] = Field(default_factory=lambda: ["viewer"])`. (This `User` model will represent a user in the system, including for responses after login or when fetching user details).
2.  Create `app/api/v1/endpoints/account_management.py`:
    *   Import `APIRouter, HTTPException, status, Depends` from `fastapi`.
    *   Import `UserCreateRequest, UserCreateResponse` from `app.models.user`. Import `UUID, uuid4` from `uuid`.
    *   Initialize `router = APIRouter(prefix="/users", tags=["Users"])`. (Note: prefix is `/users` here, not the global `/api/v1`).
    *   Implement `POST /register` endpoint (path will be `/register` relative to the router's prefix):
        *   Path operation decorator: `@router.post("/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED, summary="Register new account")`.
        *   Function signature: `async def register_user(user_in: UserCreateRequest)`.
        *   Stubbed implementation:
            *   `# TODO: Add logic to check if email already exists in DB`
            *   `# TODO: Add logic to hash password and save user to DB`
            *   `created_user_id = uuid4()`
            *   `return UserCreateResponse(userId=created_user_id, firstName=user_in.firstName, lastName=user_in.lastName, email=user_in.email)`
3.  Modify `app/main.py`:
    *   Import `account_management_router` from `app.api.v1.endpoints.account_management` (rename the router instance in `account_management.py` to `router` and then import it as `account_management_router` or similar to avoid name clashes if you plan other routers in `main.py`).
    *   Create `api_router_v1 = APIRouter(prefix=settings.API_V1_STR)`.
    *   Include the account management router: `api_router_v1.include_router(account_management.router)`.
    *   Include `api_router_v1` in the main app: `app.include_router(api_router_v1)`.
4.  Create `tests/api/v1/endpoints/test_account_management.py`:
    *   Import `AsyncClient` from `httpx`, `status` from `fastapi`.
    *   Write tests for `POST /api/v1/users/register`:
        *   Test successful registration: Send valid `UserCreateRequest` JSON data. Assert status code `201 Created`. Assert response body matches `UserCreateResponse` schema (contains `userId`, and input `firstName`, `lastName`, `email`).
        *   Test request validation errors:
            *   Send request with missing `firstName`. Assert status code `422 Unprocessable Entity`.
            *   Send request with invalid `email` format. Assert status code `422`.
            *   Send request with a short `password`. Assert status code `422`.

Current Files to Work On:
*   `app/models/user.py`
*   `app/api/v1/endpoints/account_management.py`
*   `app/main.py`
*   `tests/api/v1/endpoints/test_account_management.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 4: Password Hashing & User Service for DB Registration**
```text
Objective: Implement password hashing, create a user service for database interactions, and update the registration endpoint to save users to the (mocked) database.

Specifications:
1.  Create `app/core/security.py`:
    *   Import `CryptContext` from `passlib.context`.
    *   Initialize `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")`.
    *   Implement `def verify_password(plain_password: str, hashed_password: str) -> bool`.
    *   Implement `def get_password_hash(password: str) -> str`.
2.  Create `app/services/user_service.py`:
    *   Import `Optional, Dict, Any, List` from `typing`, `UUID, uuid4` from `uuid`, `datetime, timezone` from `datetime`.
    *   Import `get_table` from `app.db.astra_client` and `AstraDBCollection` from `astrapy.db`.
    *   Import `UserCreateRequest` from `app.models.user`.
    *   Import `get_password_hash` from `app.core.security`.
    *   Import `HTTPException, status` from `fastapi`.
    *   Define `USERS_TABLE_NAME: str = "users"` (this constant will be used with `get_table`).
    *   Implement `async def get_user_by_email_from_table(email: str, db_table: Optional[AstraDBCollection] = None) -> Optional[Dict[str, Any]]`:
        *   Accepts an optional `db_table` for easier testing/mocking. If None, calls `await get_table(USERS_TABLE_NAME)`.
        *   Calls `await db_table.find_one(filter={"email": email})`. Returns the result.
    *   Implement `async def create_user_in_table(user_in: UserCreateRequest, db_table: Optional[AstraDBCollection] = None) -> Dict[str, Any]]`:
        *   Accepts an optional `db_table`. If None, calls `await get_table(USERS_TABLE_NAME)`.
        *   Hashes password using `get_password_hash(user_in.password)`.
        *   Constructs `user_document: Dict[str, Any]` with fields: `userid` (as `str(uuid4())`), `firstName`, `lastName`, `email`, `hashed_password`, `roles=["viewer"]`, `created_at=datetime.now(timezone.utc)`.
        *   Calls `await db_table.insert_one(document=user_document)`. (Assume `insert_one` returns an object with an `inserted_id` or similar, or raises on failure. For now, focus on the call).
        *   Returns the `user_document`.
3.  Modify `app/api/v1/endpoints/account_management.py`:
    *   Import `user_service` from `app.services`.
    *   Update the `register_user` function:
        *   Call `existing_user = await user_service.get_user_by_email_from_table(email=user_in.email)`.
        *   If `existing_user`, raise `HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")`.
        *   Call `created_user_doc = await user_service.create_user_in_table(user_in=user_in)`.
        *   Return `UserCreateResponse(userId=UUID(created_user_doc["userid"]), firstName=created_user_doc["firstName"], lastName=created_user_doc["lastName"], email=created_user_doc["email"])`.
4.  Create `tests/core/test_security.py`:
    *   Write unit tests for `get_password_hash` and `verify_password`. Test that a hashed password can be verified with the original plain password, and not with a wrong one.
5.  Create `tests/services/test_user_service.py`:
    *   Import `pytest`, `unittest.mock.AsyncMock`, `unittest.mock.patch`.
    *   Import service functions and `UserCreateRequest`.
    *   Test `get_user_by_email_from_table`:
        *   Mock `AstraDBCollection.find_one`. Test when user found and not found.
    *   Test `create_user_in_table`:
        *   Mock `AstraDBCollection.insert_one`.
        *   Verify `get_password_hash` is called.
        *   Verify the structure of the document passed to `insert_one`.
        *   Verify the returned document.
6.  Modify `tests/api/v1/endpoints/test_account_management.py`:
    *   Update tests for `POST /api/v1/users/register`:
        *   Use `unittest.mock.patch` to mock `app.services.user_service.get_user_by_email_from_table` and `app.services.user_service.create_user_in_table`.
        *   Test successful registration: mock `get_user_by_email_from_table` to return `None`, mock `create_user_in_table` to return a sample user document. Assert the response.
        *   Test "Email already registered": mock `get_user_by_email_from_table` to return a dummy user document. Assert status code `400` and detail message.

Current Files to Work On:
*   `app/core/security.py`
*   `app/services/user_service.py`
*   `app/api/v1/endpoints/account_management.py`
*   `tests/core/test_security.py`
*   `tests/services/test_user_service.py`
*   `tests/api/v1/endpoints/test_account_management.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 5: JWT Implementation & Login Endpoint**```text
Objective: Implement JWT creation and validation, and the user login endpoint using the authentication service.

Specifications:
1.  Modify `app/core/config.py`:
    *   Add JWT settings to the `Settings` class: `SECRET_KEY: str`, `ALGORITHM: str = "HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES: int = 30`.
    *   Update `.env.example` with these new variables (provide a sample `SECRET_KEY` like "your-secret-key-here-pls-change-in-prod").
2.  Modify `app/core/security.py`:
    *   Import `datetime, timedelta, timezone, Union, Optional, List, Any` from `typing`.
    *   Import `jwt, JWTError` from `jose`.
    *   Import `settings` from `app.core.config`.
    *   Import `BaseModel` from `pydantic`.
    *   Define `class TokenPayload(BaseModel)`: `sub: Optional[Union[str, Any]] = None` (will hold user ID), `roles: List[str] = []`, `exp: Optional[datetime] = None`.
    *   Implement `def create_access_token(subject: Union[str, Any], roles: List[str], expires_delta: Optional[timedelta] = None) -> str`:
        *   Calculates expiry time (`expire`). If `expires_delta` is not given, use `settings.ACCESS_TOKEN_EXPIRE_MINUTES`.
        *   Creates `to_encode = TokenPayload(sub=str(subject), roles=roles, exp=expire).model_dump(exclude_none=True)`.
        *   Encodes JWT using `jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)`.
3.  Modify `app/models/user.py`:
    *   Define `class UserLoginRequest(BaseModel)`: `email: EmailStr`, `password: str`.
    *   Define `class UserLoginResponse(BaseModel)`: `token: str`, `user: User` (the `User` model defined earlier).
4.  Modify `app/services/user_service.py`:
    *   Import `User` model from `app.models.user`.
    *   Import `verify_password` from `app.core.security`.
    *   Implement `async def authenticate_user_from_table(email: str, password: str, db_table: Optional[AstraDBCollection] = None) -> Optional[User]`:
        *   Calls `user_data_dict = await get_user_by_email_from_table(email, db_table)`.
        *   If `user_data_dict` is None, return `None`.
        *   Verify password using `verify_password(password, user_data_dict["hashed_password"])`. If not verified, return `None`.
        *   If verified, map `user_data_dict` to an instance of the `User` Pydantic model and return it. Ensure all fields of `User` (like `userId`, `firstName`, `lastName`, `email`, `roles`) are correctly populated from the dictionary. `userId` in the dict is `userid`.
5.  Modify `app/api/v1/endpoints/account_management.py`:
    *   Import `UserLoginRequest, UserLoginResponse` from `app.models.user`, and `User` model.
    *   Import `create_access_token` from `app.core.security`.
    *   Implement `POST /login` endpoint:
        *   Path operation: `@router.post("/login", response_model=UserLoginResponse, summary="Login → JWT")`.
        *   Function signature: `async def login_for_access_token(form_data: UserLoginRequest)`.
        *   Call `authenticated_user = await user_service.authenticate_user_from_table(email=form_data.email, password=form_data.password)`.
        *   If `authenticated_user` is None, raise `HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})`.
        *   Create access token: `access_token = create_access_token(subject=authenticated_user.userId, roles=authenticated_user.roles)`.
        *   Return `UserLoginResponse(token=access_token, user=authenticated_user)`.
6.  In `tests/core/test_security.py`:
    *   Write unit tests for `create_access_token`. Verify the token structure by decoding it (you might need a helper to decode within tests, or just check it's a non-empty string for now if decoding is complex to set up here). Test with and without `expires_delta`.
7.  In `tests/services/test_user_service.py`:
    *   Write unit tests for `authenticate_user_from_table`:
        *   Mock `get_user_by_email_from_table` and `verify_password`.
        *   Test successful authentication (returns `User` model).
        *   Test user not found.
        *   Test incorrect password.
        *   Ensure the returned `User` model has `userId` correctly mapped from `userid` in the dict.
8.  In `tests/api/v1/endpoints/test_account_management.py`:
    *   Write integration tests for `POST /api/v1/users/login`:
        *   Mock `user_service.authenticate_user_from_table`.
        *   Test successful login: mock service to return a `User` object. Assert `200 OK`, response contains `token` and `user` object.
        *   Test authentication failure (user not found or wrong password): mock service to return `None`. Assert `401 Unauthorized`.

Current Files to Work On:
*   `app/core/config.py`
*   `.env.example`
*   `app/core/security.py`
*   `app/models/user.py`
*   `app/services/user_service.py`
*   `app/api/v1/endpoints/account_management.py`
*   `tests/core/test_security.py`
*   `tests/services/test_user_service.py`
*   `tests/api/v1/endpoints/test_account_management.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 6: Protected Route - Get User Profile**
```text
Objective: Implement JWT-based authentication for protecting routes, starting with an endpoint to get the current user's profile.

Specifications:
1.  Create `app/api/v1/dependencies.py`:
    *   Import `Annotated, List, Optional, Union, Any` from `typing`.
    *   Import `Depends, HTTPException, status` from `fastapi`.
    *   Import `OAuth2PasswordBearer` from `fastapi.security`.
    *   Import `jwt, JWTError, ExpiredSignatureError` from `jose`.
    *   Import `datetime, timezone` from `datetime`. # Added timezone
    *   Import `ValidationError` from `pydantic`.
    *   Import `settings` from `app.core.config`.
    *   Import `TokenPayload` from `app.core.security`.
    *   Import `User` from `app.models.user`.
    *   Import `user_service` from `app.services`.
    *   Import `UUID` from `uuid`.
    *   Define `reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/users/login", auto_error=False)`. Set `auto_error=False` to handle missing token manually.
    *   Implement `async def get_current_user_token_payload(token: Annotated[Optional[str], Depends(reusable_oauth2)]) -> TokenPayload`:
        *   If `token` is None (because `auto_error=False`), raise `HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")`.
        *   `try-except` block for JWT decoding:
            *   `payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])`.
            *   `token_data = TokenPayload(**payload)`.
            *   Check token expiry: `if token_data.exp and token_data.exp < datetime.now(timezone.utc): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")`.
            *   `except ExpiredSignatureError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")`.
            *   `except (JWTError, ValidationError): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")`.
        *   Return `token_data`.
    *   Implement `async def get_user_by_id_from_table(user_id: UUID, db_table: Optional[AstraDBCollection] = None) -> Optional[User]` in `app/services/user_service.py`:
        *   Accepts an optional `db_table`. If None, calls `await get_table(USERS_TABLE_NAME)`.
        *   Fetches user data dict by `userid` (as string) from table.
        *   If found, maps it to the `User` Pydantic model and returns it. Otherwise, returns `None`.
    *   Implement `async def get_current_user_from_token(payload: Annotated[TokenPayload, Depends(get_current_user_token_payload)]) -> User`:
        *   If `payload.sub` is None, raise `HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")`.
        *   Call `user = await user_service.get_user_by_id_from_table(user_id=UUID(payload.sub))`.
        *   If `user` is None, raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")`.
        *   Return `user`.
2.  Modify `app/models/user.py`:
    *   Define `class UserProfile(UserBase)`: Add `userId: UUID`. This model can be used if you want a specific subset of fields for the profile, otherwise the `User` model can be returned. For now, let's plan to return the `User` model directly.
3.  Modify `app/api/v1/endpoints/account_management.py`:
    *   Import `User` from `app.models.user`.
    *   Import `get_current_user_from_token` from `app.api.v1.dependencies`.
    *   Import `Annotated` from `typing`.
    *   Implement `GET /me` endpoint:
        *   Path operation: `@router.get("/me", response_model=User, summary="Current user profile")`.
        *   Function signature: `async def read_users_me(current_user: Annotated[User, Depends(get_current_user_from_token)])`.
        *   Return `current_user`.
4.  Create `tests/api/v1/test_dependencies.py`:
    *   Write unit tests for `get_current_user_token_payload` and `get_current_user_from_token`.
    *   Mock `jwt.decode`, `user_service.get_user_by_id_from_table`, and `settings`.
    *   Test valid token, expired token, invalid token format, missing token, token with no subject, user not found in DB.
5.  Modify `tests/api/v1/endpoints/test_account_management.py`:
    *   Add integration tests for `GET /api/v1/users/me`:
        *   Helper function to create a valid JWT for a test user.
        *   Test with a valid token: Mock `user_service.get_user_by_id_from_table` to return a test `User` object. Assert `200 OK` and correct user data in response.
        *   Test with no token: Assert `401 Unauthorized`.
        *   Test with an invalid/malformed token: Assert `401 Unauthorized`.
        *   Test with an expired token: Assert `401 Unauthorized`.
        *   Test with a valid token but user not found in DB: Mock service to return `None`. Assert `404 Not Found`.

Current Files to Work On:
*   `app/api/v1/dependencies.py`
*   `app/services/user_service.py` (add `get_user_by_id_from_table`)
*   `app/api/v1/endpoints/account_management.py`
*   `tests/api/v1/test_dependencies.py`
*   `tests/api/v1/endpoints/test_account_management.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 7: Update User Profile**
```text
Objective: Implement the endpoint for users to update their own profile information.

Specifications:
1.  Modify `app/models/user.py`:
    *   Define `class UserProfileUpdateRequest(BaseModel)`:
        *   `firstName: Optional[str] = Field(None, min_length=1, max_length=50)`
        *   `lastName: Optional[str] = Field(None, min_length=1, max_length=50)`
        *   (Note: Email updates are complex due to verification and uniqueness, so we'll omit email update for now unless specified otherwise).
2.  Modify `app/services/user_service.py`:
    *   Import `UserProfileUpdateRequest` from `app.models.user`.
    *   Implement `async def update_user_in_table(user_id: UUID, update_data: UserProfileUpdateRequest, db_table: Optional[AstraDBCollection] = None) -> Optional[User]`:
        *   Accepts an optional `db_table`. If None, calls `await get_table(USERS_TABLE_NAME)`.
        *   Fetches the current user document using `await db_table.find_one(filter={"userid": str(user_id)})`. If not found, return `None`.
        *   Creates `update_fields = update_data.model_dump(exclude_unset=True)`. This gets only the fields provided in the request.
        *   If `update_fields` is not empty:
            *   Calls `await db_table.update_one(filter={"userid": str(user_id)}, update={"$set": update_fields})`.
            *   Refetch the updated user document: `updated_user_doc = await db_table.find_one(filter={"userid": str(user_id)})`.
            *   Map `updated_user_doc` to the `User` Pydantic model and return it.
        *   If `update_fields` is empty, map the original `user_data_dict` (from the first fetch) to `User` model and return it (no update needed).
3.  Modify `app/api/v1/endpoints/account_management.py`:
    *   Import `UserProfileUpdateRequest` from `app.models.user`.
    *   Implement `PUT /me` endpoint:
        *   Path operation: `@router.put("/me", response_model=User, summary="Update profile")`.
        *   Function signature: `async def update_users_me(profile_update_data: UserProfileUpdateRequest, current_user: Annotated[User, Depends(get_current_user_from_token)])`.
        *   Call `updated_user = await user_service.update_user_in_table(user_id=current_user.userId, update_data=profile_update_data)`.
        *   If `updated_user` is `None` (shouldn't happen if `current_user` dependency worked, but good for safety), raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found for update")`.
        *   Return `updated_user`.
4.  In `tests/services/test_user_service.py`:
    *   Write unit tests for `update_user_in_table`:
        *   Mock `AstraDBCollection.find_one` and `AstraDBCollection.update_one`.
        *   Test successful update with some fields. Verify `update_one` is called with correct `$set` payload. Verify returned `User` model.
        *   Test with no fields in `update_data` (should still return the user, no `update_one` call).
        *   Test user not found initially.
5.  In `tests/api/v1/endpoints/test_account_management.py`:
    *   Add integration tests for `PUT /api/v1/users/me`:
        *   Use a helper to get a valid token for a test user. Mock `user_service.update_user_in_table`.
        *   Test successful update: Send valid `UserProfileUpdateRequest`. Mock service to return an updated `User` object. Assert `200 OK` and correct user data in response.
        *   Test with empty update data: Assert `200 OK` and original user data.
        *   Test with invalid data in `UserProfileUpdateRequest` (e.g., `firstName` too long if you add more validation to the model): Assert `422 Unprocessable Entity`.
        *   Test access with no token / invalid token (should be caught by dependency).

Current Files to Work On:
*   `app/models/user.py`
*   `app/services/user_service.py`
*   `app/api/v1/endpoints/account_management.py`
*   `tests/services/test_user_service.py`
*   `tests/api/v1/endpoints/test_account_management.py`

Provide the complete content for each new/modified file.
```
---
**Prompt 8: RBAC Foundation**
```text
Objective: Establish the foundation for Role-Based Access Control (RBAC) by ensuring roles are part of the user model and token, and by creating a basic role-checking dependency.

Specifications:
1.  Verify/Ensure in `app/core/security.py`:
    *   `TokenPayload` class includes `roles: List[str] = []`.
    *   `create_access_token` function accepts `roles: List[str]` and includes it in the `TokenPayload` when creating the JWT.
2.  Verify/Ensure in `app/models/user.py`:
    *   The `User` Pydantic model includes `roles: List[str] = Field(default_factory=list)`. (If default was `["viewer"]`, adjust to `default_factory=list` and ensure DB record is source of truth).
3.  Modify `app/services/user_service.py`:
    *   In `create_user_in_table`: Ensure the `user_document` saved to the database includes `roles=["viewer"]` by default.
    *   In `authenticate_user_from_table` and `get_user_by_id_from_table`: Ensure that the `roles` field from the database document is correctly mapped to the `roles` field of the returned `User` Pydantic model. If `roles` is missing from DB doc, default to `[]` or `["viewer"]` as appropriate for your logic.
4.  Modify `app/api/v1/dependencies.py`:
    *   Implement `def require_role(required_roles: List[str])`:
        *   This function will be a dependency factory. It should return an inner asynchronous function `async def role_checker(current_user: Annotated[User, Depends(get_current_user_from_token)]) -> User:`.
        *   Inside `role_checker`:
            *   If `not current_user.roles`: raise `HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no roles assigned")`.
            *   Check if `any(role in current_user.roles for role in required_roles)`.
            *   If the check fails (user does not have at least one of the required roles), raise `HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"User does not have required roles: {required_roles}")`.
            *   If the check passes, return `current_user`.
    *   Define specific role dependencies using the factory:
        *   `async def get_current_viewer(current_user: Annotated[User, Depends(require_role(["viewer", "creator", "moderator"]))]) -> User: return current_user`
        *   `async def get_current_creator(current_user: Annotated[User, Depends(require_role(["creator", "moderator"]))]) -> User: return current_user`
        *   `async def get_current_moderator(current_user: Annotated[User, Depends(require_role(["moderator"]))]) -> User: return current_user`
        *   (Note: For this step, only `get_current_viewer` will be actively used and tested with the "viewer" role).
5.  Modify `app/api/v1/endpoints/account_management.py`:
    *   Change the dependency for `read_users_me` and `update_users_me` from `current_user: Annotated[User, Depends(get_current_user_from_token)]` to `current_user: Annotated[User, Depends(get_current_viewer)]`.
6.  In `tests/api/v1/test_dependencies.py`:
    *   Write unit tests for `require_role` and the derived dependencies (`get_current_viewer`).
    *   Mock `get_current_user_from_token` to return users with different roles.
    *   Test scenarios:
        *   User has required role.
        *   User does not have required role.
        *   User has no roles.
        *   User has one of several allowed roles.
7.  In `tests/api/v1/endpoints/test_account_management.py`:
    *   Update tests for `GET /me` and `PUT /me`:
        *   Ensure they still pass when the user has the "viewer" role (mock `get_current_user_from_token` within the mocked `get_current_viewer` dependency chain, or mock `get_current_viewer` directly to return a user with "viewer" role).
        *   (Optional, for completeness) Add a test where `get_current_viewer` is mocked to simulate a user without the "viewer" role (or any role from its list), expecting a 403. This might involve more complex mocking of the dependency chain.

Current Files to Work On:
*   `app/core/security.py` (Verification)
*   `app/models/user.py` (Verification/Adjustment)
*   `app/services/user_service.py`
*   `app/api/v1/dependencies.py`
*   `app/api/v1/endpoints/account_management.py`
*   `tests/api/v1/test_dependencies.py`
*   `tests/api/v1/endpoints/test_account_management.py`

Provide the complete content for each new/modified file.
```

This concludes the prompts for Phase 0 and Epic 1. Subsequent epics (Video Catalog, Comments, etc.) would follow a similar pattern of defining models, then services, then API endpoints, and finally tests for each chunk of functionality.