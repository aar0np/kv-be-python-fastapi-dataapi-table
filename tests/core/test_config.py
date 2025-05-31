import os
import pytest


# Temporarily set environment variables for testing
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "Test Project From Env")
    # Ensure config is reloaded by importing after env vars are set
    from app.core import config

    # Reload settings if your config system supports it or re-instantiate
    config.settings = config.Settings()
    yield
    # Clean up by re-importing original settings or resetting
    config.settings = config.Settings(
        _env_file=None
    )  # Attempt to load without .env to get defaults


def test_settings_load_from_env():
    from app.core.config import settings

    assert settings.PROJECT_NAME == "Test Project From Env"


def test_settings_default_value():
    # This test assumes that if .env is not present or var is not in .env,
    # the default from the Settings class is used.
    # To make this test independent, we ensure no .env influences it.
    # We can achieve this by temporarily disabling .env loading or using a non-existent .env file path

    from app.core.config import Settings
    # Instantiate settings without relying on a .env file for this specific test
    # This requires Pydantic settings to allow ignoring .env if specified
    # or by ensuring no .env file exists that pytest can see.

    # For a cleaner test, let's ensure no ENV VAR is set for API_V1_STR
    if "API_V1_STR" in os.environ:
        del os.environ["API_V1_STR"]

    # Re-instantiate settings to pick up the default, not from env or a .env file
    # This assumes Settings can be instantiated in a way that ignores .env for testing purposes.
    # A common way is to pass _env_file=None or a path to a non-existent .env file.
    settings_with_defaults = Settings(_env_file=None)  # Pydantic-settings feature

    assert settings_with_defaults.API_V1_STR == "/api/v1"
