"""API route package."""

from fastapi import APIRouter

from backend.api.routes import analysis, health, rag, upload

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(upload.router)
api_router.include_router(analysis.router)
api_router.include_router(rag.router)

__all__ = ["api_router"]
