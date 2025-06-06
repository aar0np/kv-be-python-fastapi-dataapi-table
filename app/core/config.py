from pydantic_settings import BaseSettings
from app.version import __version__ as app_version


class Settings(BaseSettings):
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
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Application build version (surfaced in OpenAPI docs)
    APP_VERSION: str = app_version

    class Config:
        env_file = ".env"


settings = Settings()
