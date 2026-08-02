"""FastAPI shared dependencies."""

from backend.models.database import get_db
from backend.utils.config import Settings, get_settings


def get_app_settings() -> Settings:
    return get_settings()


__all__ = ["get_db", "get_app_settings"]
