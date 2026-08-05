"""Health check routes."""

from fastapi import APIRouter, Depends

from backend.api.deps import get_app_settings
from backend.models.schemas import HealthResponse
from backend.utils.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    status = "ok"
    if settings.llm_provider == "openai" and not settings.openai_api_key.strip():
        status = "degraded"
    return HealthResponse(
        status=status,
        app_name=settings.app_name,
        environment=settings.app_env,
        llm_provider=settings.llm_provider,
    )
