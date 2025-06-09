import logging
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.astra_client import init_astra_db
from app.models.common import ProblemDetail
from app.api.v1.endpoints.account_management import (
    router as account_management_router,
)

logger = logging.getLogger(__name__)

service_app = FastAPI(
    title="KillrVideo - User Service",
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/users/openapi.json",
)

# CORS – open for demo purposes; tighten in prod
service_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router(s)
service_app.include_router(account_management_router, prefix=settings.API_V1_STR)


@service_app.on_event("startup")
async def startup_event() -> None:
    await init_astra_db()


@service_app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):  # noqa: D401
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


@service_app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):  # noqa: D401
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
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


@service_app.get("/", summary="Health check")
async def service_root():
    """Simple heartbeat endpoint."""

    return {"service": "user", "status": "healthy"}
