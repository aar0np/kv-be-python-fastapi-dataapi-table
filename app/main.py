import logging
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request, status, APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.astra_client import init_astra_db
from app.models.common import ProblemDetail
from app.api.v1.endpoints import account_management, video_catalog, search_catalog, comments_ratings

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# API router for v1
api_router_v1 = APIRouter(prefix=settings.API_V1_STR)
api_router_v1.include_router(account_management.router)
api_router_v1.include_router(video_catalog.router)
api_router_v1.include_router(search_catalog.router)
api_router_v1.include_router(comments_ratings.router)

app.include_router(api_router_v1)


@app.on_event("startup")
async def startup_event():
    await init_astra_db()


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


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
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


@app.get("/", summary="Health check")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}
