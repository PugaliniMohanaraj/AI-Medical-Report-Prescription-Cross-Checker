"""SQLAlchemy ORM entities."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UploadedFileRecord(Base):
    """Metadata for a stored upload (PDF or image)."""

    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )


class VisitExtractionRecord(Base):
    """Structured extraction result for one uploaded document / visit."""

    __tablename__ = "visit_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_file_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    visit_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    patient_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hospital: Mapped[str | None] = mapped_column(String(256), nullable=True)
    doctor: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    extraction_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    full_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
