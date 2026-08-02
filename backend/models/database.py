"""SQLAlchemy database setup (SQLite metadata store)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.utils.config import get_settings
from backend.utils.paths import resolve_path


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def get_database_url() -> str:
    settings = get_settings()
    db_path = resolve_path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # aiosqlite async driver — use forward slashes for SQLAlchemy URL
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


engine = create_async_engine(get_database_url(), echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables for registered ORM entities."""
    # Import entities so metadata is populated before create_all.
    from backend.models import entities as _entities  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
