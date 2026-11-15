"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.content import load_all as load_content
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import AppError
from app.routers import (
    account,
    activity,
    auth,
    checkins,
    habits,
    health,
    history,
    milestones,
    nutrition,
    profile,
    runs,
    today,
    training,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_content()
    yield
    await engine.dispose()


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        {"detail": exc.message, "code": exc.code}, status_code=exc.status_code, headers=headers
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.version,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_exception_handler(AppError, _app_error_handler)
    for r in (
        health.router,
        auth.router,
        profile.router,
        today.router,
        activity.router,
        runs.router,
        checkins.router,
        milestones.router,
        training.router,
        nutrition.router,
        habits.router,
        history.router,
        account.router,
    ):
        app.include_router(r, prefix=settings.api_prefix)
    return app


app = create_app()
