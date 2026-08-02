"""Medical Report & Prescription Cross-Checker — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import api_router
from backend.models.database import init_db
from backend.utils.config import get_settings
from backend.utils.paths import resolve_path


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup / shutdown hooks."""
    settings = get_settings()
    resolve_path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    resolve_path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    resolve_path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
