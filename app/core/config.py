import pathlib
import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.version import __version__ as app_version
from pydantic import Field
from pydantic import model_validator

# --------------------------------------------------------------
# Root logging configuration
# --------------------------------------------------------------
# Honour a LOG_LEVEL environment variable (default INFO) so that running e.g.
#   $ export LOG_LEVEL=DEBUG
# surfaces debug-level log lines from all project modules without requiring a
# custom uvicorn logging config.  We set this up before the rest of the app is
# imported to ensure it governs all subsequent logger instances.

_root_log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

# Only configure the root logger if it hasn't been configured yet (to avoid
# clobbering test-specific logging setups).
if not logging.getLogger().hasHandlers():  # pragma: no cover
    logging.basicConfig(
        level=_root_log_level, format="%(levelname)s:%(name)s:%(message)s"
    )
else:
    # Some other subsystem (e.g. pytest, uvicorn) already configured handlers;
    # we still honour our desired verbosity by adjusting the root level.
    logging.getLogger().setLevel(_root_log_level)

# Build a definitive, absolute path to the .env file.
# This starts from the location of THIS file (config.py) and walks up
# the directory tree to the project root, then appends ".env".
# This makes loading the .env file completely independent of the
# current working directory, which is essential for `uvicorn --reload`.
try:
    _project_root = pathlib.Path(__file__).parent.parent.parent
    _ENV_FILE = _project_root / ".env"
    logging.debug(f"Looking for .env file at {_ENV_FILE}")
    if not _ENV_FILE.is_file():
        # Fallback for safety, though it shouldn't be needed with this logic.
        _ENV_FILE = ".env"
        logging.warning(f"No .env file found at {_ENV_FILE}, using default .env file")
except NameError:
    _ENV_FILE = ".env"
    logging.warning(f"No .env file found at {_ENV_FILE}, using default .env file")


class Settings(BaseSettings):
    # Pydantic-settings model. Populates settings from .env file and environment
    # variables.  See: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "KillrVideo Python FastAPI Backend"
    API_V1_STR: str = "/api/v1"

    # AstraDB Settings
    ASTRA_DB_API_ENDPOINT: str = "http://localhost:8080/api"  # Dummy default for tests
    ASTRA_DB_APPLICATION_TOKEN: str = "test-token"  # Dummy default for tests
    ASTRA_DB_KEYSPACE: str = "test_keyspace"  # Dummy default for tests

    # JWT Settings
    SECRET_KEY: str = "unit-test-secret"  # Dummy default for tests
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # CORS – provide comma-separated string in env ("*" for all)
    CORS_ALLOW_ORIGINS: str = "*"

    @property
    def parsed_cors_origins(self) -> list[str]:  # noqa: D401
        raw = self.CORS_ALLOW_ORIGINS
        if raw.strip() == "*":
            return ["*"]
        origins = []
        for o in raw.split(","):
            o_strip = o.strip()
            if not o_strip:
                continue
            # Normalize by removing any trailing slash so that
            # "http://localhost:8080/" and "http://localhost:8080" match.
            if o_strip.endswith("/"):
                o_strip = o_strip.rstrip("/")
            origins.append(o_strip)
        return origins

    # Application build version (surfaced in OpenAPI docs)
    APP_VERSION: str = app_version

    ENVIRONMENT: str = Field(default="dev")

    # ------------------------------------------------------------------
    # Video metadata processing toggles (used by video_service)
    # ------------------------------------------------------------------

    INLINE_METADATA_DISABLED: bool = False
    ENABLE_BACKGROUND_PROCESSING: bool = True
    # Feature flag – enables semantic vector search endpoints
    VECTOR_SEARCH_ENABLED: bool = False

    # ------------------------------------------------------------------
    # YouTube integration
    # ------------------------------------------------------------------

    YOUTUBE_API_KEY: str | None = Field(
        default=None,
        description="API key for YouTube Data API v3. If unset, service falls back to oEmbed.",
    )

    YOUTUBE_API_TIMEOUT: float = Field(
        default=3.0,
        description="Timeout (seconds) for outbound YouTube HTTP requests.",
        ge=0.5,
    )

    # ------------------------------------------------------------------
    # Pydantic hook: coerce boolean env vars that may carry inline
    # descriptors (e.g. "false   # keep inline fetch") coming from env
    # files.  We strip everything after the first whitespace/# so the
    # builtin bool parser sees a clean "true" / "false" token.
    # ------------------------------------------------------------------

    @model_validator(mode="before")
    @classmethod
    def _sanitize_bool_tokens(cls, data):  # type: ignore[return-value]
        for key in (
            "INLINE_METADATA_DISABLED",
            "ENABLE_BACKGROUND_PROCESSING",
            "VECTOR_SEARCH_ENABLED",
        ):
            if key in data and isinstance(data[key], str):
                raw = data[key]
                # Split at first whitespace or '#'
                token = raw.split("#", 1)[0].strip().split()[0]
                data[key] = token
        return data


settings = Settings()
