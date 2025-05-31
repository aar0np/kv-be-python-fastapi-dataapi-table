from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"


settings = Settings()
