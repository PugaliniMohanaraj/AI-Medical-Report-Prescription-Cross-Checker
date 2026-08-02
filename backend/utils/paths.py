"""Path helpers for data directories."""

from pathlib import Path

from backend.utils.config import REPO_ROOT, Settings, get_settings


def resolve_path(path: str, _settings: Settings | None = None) -> Path:
    """Resolve a configured path relative to the repository root when not absolute."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (REPO_ROOT / candidate).resolve()


def get_upload_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    directory = resolve_path(settings.upload_dir, settings)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
