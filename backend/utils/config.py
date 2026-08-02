"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
_ENV_FILES = (
    str(BACKEND_DIR / ".env"),
    str(REPO_ROOT / ".env"),
)


class Settings(BaseSettings):
    """Central settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Medical Report Cross-Checker"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM
    llm_provider: Literal["ollama", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # Paths (resolved relative to repo root when not absolute)
    upload_dir: str = "backend/uploads"
    chroma_persist_dir: str = "backend/data/chroma"
    chroma_collection_name: str = "medical_reports"
    sqlite_db_path: str = "backend/data/metadata.db"

    # Limits
    max_upload_size_mb: int = 20
    max_files_per_request: int = 10

    # PDF extraction / OCR
    pdf_min_text_chars: int = 1
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    ocr_dpi: int = 300
    tessdata_path: str = ""

    # Lab trends
    lab_ai_explanations_enabled: bool = True

    # RAG
    rag_vector_backend: Literal["auto", "chroma", "memory"] = "auto"
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_default_top_k: int = 5

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
