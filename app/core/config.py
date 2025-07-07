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
            "OBSERVABILITY_ENABLED",
            "OTEL_TRACES_ENABLED",
            "OTEL_METRICS_ENABLED",
            "LOKI_ENABLED",
        ):
            if key in data and isinstance(data[key], str):
                raw = data[key]
                # Split at first whitespace or '#'
                token = raw.split("#", 1)[0].strip().split()[0]
                data[key] = token
        return data

    # ------------------------------------------------------------------
    # Observability / Telemetry
    # ------------------------------------------------------------------

    # Master on/off switch – when false no observability instrumentation is
    # initialised.  This is useful for local development or extremely
    # resource-constrained environments where you don't want the overhead of
    # telemetry.
    OBSERVABILITY_ENABLED: bool = Field(
        default=True,
        description="Globally enable/disable all extra observability (metrics/traces/log shipping).",
    )

    # --- OpenTelemetry ---------------------------------------------------

    # OTLP endpoint that traces / metrics will be sent to.  For the Docker
    # Compose stack provided by the `mcp-observability` project this will be
    # the OpenTelemetry Collector service – typically http://otelcol:4317.
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(
        default=None,
        description="Base OTLP gRPC endpoint, e.g. http://otelcol:4317.  If unset OTLP export is disabled.",
    )

    # Toggle exporting OpenTelemetry traces.  Requires OTEL_EXPORTER_OTLP_ENDPOINT.
    OTEL_TRACES_ENABLED: bool = True

    # Toggle exporting OpenTelemetry metrics via OTLP.  The Prometheus scrape
    # endpoint (provided by prometheus-fastapi-instrumentator) remains active
    # regardless of this flag so that a local Prometheus instance can still
    # pull metrics if desired.
    OTEL_METRICS_ENABLED: bool = False

    # Protocol for OTLP export – "grpc" (default) or "http". Allows integration with collectors that only expose the HTTP/JSON OTLP endpoint (4318).
    OTEL_EXPORTER_OTLP_PROTOCOL: str = Field(default="grpc")

    # Optional additional headers to send along OTLP requests (for auth tokens, etc.).
    # Provide as comma-separated key=value list, e.g. "mcp-token=abcd123,env=dev".
    OTEL_EXPORTER_OTLP_HEADERS: str | None = Field(default=None)

    # Sample ratio (0.0-1.0) for traces – 1.0 = always.
    OTEL_TRACES_SAMPLER_RATIO: float = Field(default=1.0, ge=0.0, le=1.0)

    # --- Centralised logging (Loki) --------------------------------------

    LOKI_ENABLED: bool = Field(
        default=False, description="Enable structured log shipping to Loki."
    )
    LOKI_ENDPOINT: str | None = Field(
        default=None,
        description="Loki push API endpoint, e.g. http://loki:3100/loki/api/v1/push.",
    )

    # Extra labels to attach to Loki log streams – provided as a comma-separated
    # list of key=value pairs so they can be conveniently set via environment
    # variables.
    LOKI_EXTRA_LABELS: str | None = Field(default=None)


settings = Settings()
