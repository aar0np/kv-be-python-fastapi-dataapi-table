"""KillrVideo monolithic FastAPI application.

This file assembles **all** routers from the various domain services into a
single FastAPI instance.  It is ideal for local development and testing or for
deployments that prefer a unified 'monolith' instead of separate micro-services.

If you intend to run the new micro-service containers, use their dedicated
entry-points (e.g. ``app.main_user:service_app``) instead.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request, status, APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.astra_client import init_astra_db
from app.models.common import ProblemDetail
from app.api.v1.endpoints import (
    account_management,
    video_catalog,
    search_catalog,
    comments_ratings,
    recommendations_feed,
    reco_internal,
    flags,
    moderation,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="KillrVideo v2 - Monolith Backend", version=settings.APP_VERSION)

# ---------------------------------------------------------------------------
# CORS middleware
#
# See: https://fastapi.tiangolo.com/tutorial/cors/
# ---------------------------------------------------------------------------

logger.debug(f"CORS origins: {settings.parsed_cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router for v1
api_router_v1 = APIRouter(prefix=settings.API_V1_STR)
api_router_v1.include_router(account_management.router)
api_router_v1.include_router(video_catalog.router)
api_router_v1.include_router(search_catalog.router)
api_router_v1.include_router(comments_ratings.router)
api_router_v1.include_router(recommendations_feed.router)
api_router_v1.include_router(reco_internal.router)
api_router_v1.include_router(flags.router)
api_router_v1.include_router(moderation.router)

app.include_router(api_router_v1)

# Attempt to import httpx & httpcore connection error classes for fine-grained
# exception handling.  They may not be present in some lightweight test
# environments – fall back gracefully.

try:
    import httpx  # type: ignore

    HttpxConnectError = httpx.ConnectError
except ModuleNotFoundError:  # pragma: no cover
    httpx = None  # type: ignore
    HttpxConnectError = None  # type: ignore

try:
    from httpcore import ConnectError as HttpcoreConnectError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    HttpcoreConnectError = None  # type: ignore


@app.on_event("startup")
async def startup_event():
    await init_astra_db()

    # ------------------------------------------------------------------
    # Debug – dump env vars and settings so we can verify flags like
    # INLINE_METADATA_DISABLED / ENABLE_BACKGROUND_PROCESSING are picked up.
    # Sensitive values containing keywords are masked to avoid leaking
    # secrets in logs.
    # ------------------------------------------------------------------

    def _mask(value: str) -> str:  # noqa: D401
        SENSITIVE_KEYWORDS = {"KEY", "TOKEN", "SECRET", "PASSWORD"}
        return "***" if any(k in value.upper() for k in SENSITIVE_KEYWORDS) else value

    import os  # noqa: E402
    import json  # noqa: E402

    env_dump = {k: _mask(v) for k, v in os.environ.items()}
    logger.debug("Environment variables at startup: %s", json.dumps(env_dump, indent=2))

    settings_dump = settings.model_dump()
    logger.debug(
        "Pydantic settings at startup: %s", json.dumps(settings_dump, indent=2)
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ProblemDetail(
            type="about:blank",
            title=HTTPStatus(exc.status_code).phrase,
            status=exc.status_code,
            detail=exc.detail,
            instance=str(request.url),
        ).model_dump(exclude_none=True),
    )


async def _problem_response(request: Request, status_code: int, detail: str):
    """Helper to build RFC7807-style JSON error bodies."""

    return JSONResponse(
        status_code=status_code,
        content=ProblemDetail(
            type="about:blank",
            title=HTTPStatus(status_code).phrase,
            status=status_code,
            detail=detail,
            instance=str(request.url),
        ).model_dump(exclude_none=True),
    )


if HttpxConnectError is not None:

    @app.exception_handler(HttpxConnectError)  # type: ignore[arg-type]
    async def httpx_connect_error_handler(
        request: Request, exc: Exception
    ):  # noqa: D401
        logger.warning("AstraDB connectivity problem: %s", exc)
        # Provide more context for troubleshooting: log the failed request (if
        # available) and the full stack trace at DEBUG level.
        if hasattr(exc, "request") and exc.request is not None:  # pragma: no cover
            logger.debug(
                "Failed AstraDB request – %s %s", exc.request.method, exc.request.url
            )
        logger.debug("Detailed stack trace for connectivity issue:", exc_info=True)
        return await _problem_response(
            request,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to reach data store. Please try again later.",
        )


if HttpcoreConnectError is not None:

    @app.exception_handler(HttpcoreConnectError)  # type: ignore[arg-type]
    async def httpcore_connect_error_handler(
        request: Request, exc: Exception
    ):  # noqa: D401
        logger.warning("AstraDB connectivity problem: %s", exc)
        # httpcore.ConnectError does not expose the original request object, but we
        # still output the stack trace to aid debugging.
        logger.debug("Detailed stack trace for connectivity issue:", exc_info=True)
        return await _problem_response(
            request,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to reach data store. Please try again later.",
        )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ProblemDetail(
            type="about:blank",
            title=HTTPStatus.INTERNAL_SERVER_ERROR.phrase,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
            instance=str(request.url),
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors and return a default 422 response."""
    logger.error("Request validation failed: %s", exc.errors())
    # Re-raise the original exception to let FastAPI handle the default response
    # This keeps the response format consistent with FastAPI's built-in validation.
    # For a custom response, you would build and return a JSONResponse here.
    from fastapi.exception_handlers import request_validation_exception_handler

    return await request_validation_exception_handler(request, exc)


@app.get("/", summary="Health check")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}
