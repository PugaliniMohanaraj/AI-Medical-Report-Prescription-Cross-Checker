"""Medical Report & Prescription Cross-Checker — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    async def root():
        """Friendly landing for the API host (avoids bare 404 on Render URL)."""
        return {
            "app": settings.app_name,
            "status": "ok",
            "health": f"{settings.api_prefix}/health",
            "docs": "/docs",
            "api_prefix": settings.api_prefix,
        }

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return RedirectResponse(url="/docs")

    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
