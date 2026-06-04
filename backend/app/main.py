import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.redis import close_redis
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
            "version": __version__,
        }

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    app.mount(
        settings.MEDIA_URL_PREFIX,
        StaticFiles(directory=settings.MEDIA_ROOT),
        name="media",
    )

    return app


app = create_app()
