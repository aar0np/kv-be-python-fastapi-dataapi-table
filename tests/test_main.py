import pytest
from httpx import AsyncClient
from fastapi import status, HTTPException
from http import HTTPStatus

from app.main import app  # Assuming your FastAPI app instance is named 'app'
from app.core.config import settings
from app.models.common import ProblemDetail


# Fixture to add temporary routes for testing exception handlers
@pytest.fixture(scope="function")  # Use function scope to add/remove routes per test
def add_exc_testing_routes():
    # Temporary routes for testing exception handlers
    @app.get("/test_http_exception")
    async def route_test_http_exception():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found here"
        )

    @app.get("/test_generic_exception")
    async def route_test_generic_exception():
        raise ValueError("A generic value error occurred")

    # Clean up: No direct way to remove routes in FastAPI without recreating app.
    # For testing, this is usually fine. If problematic, consider app factory pattern.
    yield


@pytest.mark.asyncio
async def test_root_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Welcome to {settings.PROJECT_NAME}!"}


@pytest.mark.asyncio
async def test_http_exception_handler(add_exc_testing_routes):  # Use the fixture
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/test_http_exception")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    problem = ProblemDetail(**response.json())
    assert problem.title == HTTPStatus.NOT_FOUND.phrase
    assert problem.status == status.HTTP_404_NOT_FOUND
    assert problem.detail == "Item not found here"
    assert "/test_http_exception" in problem.instance


@pytest.mark.asyncio
async def test_generic_exception_handler(add_exc_testing_routes):  # Use the fixture
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/test_generic_exception")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    problem = ProblemDetail(**response.json())
    assert problem.title == HTTPStatus.INTERNAL_SERVER_ERROR.phrase
    assert problem.status == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert problem.detail == "An unexpected internal server error occurred."
    assert "/test_generic_exception" in problem.instance
