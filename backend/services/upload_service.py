"""PDF upload storage and validation service."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entities import UploadedFileRecord
from backend.models.schemas import UploadedFileInfo
from backend.utils.config import Settings, get_settings
from backend.utils.paths import get_upload_dir

PDF_MAGIC = b"%PDF"
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
}
_UNSAFE_FILENAME = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)


class UploadValidationError(Exception):
    """Raised when one or more uploaded files fail validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class UploadService:
    """Validate, persist, and track uploaded PDF files."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.upload_dir = get_upload_dir(self.settings)
        self.max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        self.max_files = self.settings.max_files_per_request

    async def save_uploads(
        self,
        files: list[UploadFile],
        db: AsyncSession,
    ) -> list[UploadedFileInfo]:
        if not files:
            raise UploadValidationError(["No files provided."])

        if len(files) > self.max_files:
            raise UploadValidationError(
                [f"Too many files. Maximum allowed per request is {self.max_files}."]
            )

        # Read + validate all files before writing anything (atomic batch).
        prepared: list[tuple[UploadFile, bytes, str]] = []
        errors: list[str] = []

        for index, upload in enumerate(files, start=1):
            label = upload.filename or f"file_{index}"
            try:
                raw = await upload.read()
                self._validate_file(label, upload.content_type, raw)
                prepared.append((upload, raw, label))
            except UploadValidationError as exc:
                errors.extend(exc.errors)
            finally:
                await upload.close()

        if errors:
            raise UploadValidationError(errors)

        saved: list[UploadedFileInfo] = []
        written_paths: list[Path] = []

        try:
            for upload, raw, label in prepared:
                info, path = await self._persist_one(upload, raw, label, db)
                written_paths.append(path)
                saved.append(info)
            await db.commit()
        except Exception:
            await db.rollback()
            for path in written_paths:
                path.unlink(missing_ok=True)
            raise

        return saved

    async def list_uploads(self, db: AsyncSession) -> list[UploadedFileInfo]:
        result = await db.execute(
            select(UploadedFileRecord).order_by(UploadedFileRecord.uploaded_at.desc())
        )
        rows = result.scalars().all()
        return [self._to_info(row) for row in rows]

    async def get_upload(self, file_id: str, db: AsyncSession) -> UploadedFileInfo | None:
        row = await db.get(UploadedFileRecord, file_id)
        if row is None:
            return None
        return self._to_info(row)

    async def delete_upload(self, file_id: str, db: AsyncSession) -> bool:
        row = await db.get(UploadedFileRecord, file_id)
        if row is None:
            return False

        path = self.upload_dir / row.stored_filename
        await db.delete(row)
        await db.commit()
        path.unlink(missing_ok=True)
        return True

    def _validate_file(self, filename: str, content_type: str | None, raw: bytes) -> None:
        errors: list[str] = []

        if not filename.lower().endswith(".pdf"):
            errors.append(f"'{filename}' must have a .pdf extension.")

        normalized_ct = (content_type or "").split(";")[0].strip().lower()
        if normalized_ct and normalized_ct not in ALLOWED_CONTENT_TYPES | {
            "application/octet-stream",
        }:
            errors.append(
                f"'{filename}' has unsupported content type '{content_type}'."
            )

        if not raw:
            errors.append(f"'{filename}' is empty.")
        elif len(raw) > self.max_bytes:
            errors.append(
                f"'{filename}' exceeds the {self.settings.max_upload_size_mb} MB size limit."
            )
        elif not raw.lstrip().startswith(PDF_MAGIC):
            errors.append(f"'{filename}' is not a valid PDF file.")

        if errors:
            raise UploadValidationError(errors)

    async def _persist_one(
        self,
        upload: UploadFile,
        raw: bytes,
        label: str,
        db: AsyncSession,
    ) -> tuple[UploadedFileInfo, Path]:
        file_id = str(uuid.uuid4())
        safe_name = self._sanitize_filename(label)
        stored_filename = f"{file_id}.pdf"
        destination = self.upload_dir / stored_filename
        checksum = hashlib.sha256(raw).hexdigest()
        uploaded_at = datetime.now(timezone.utc)

        async with aiofiles.open(destination, "wb") as handle:
            await handle.write(raw)

        record = UploadedFileRecord(
            id=file_id,
            original_filename=safe_name,
            stored_filename=stored_filename,
            content_type="application/pdf",
            size_bytes=len(raw),
            checksum_sha256=checksum,
            uploaded_at=uploaded_at,
        )
        db.add(record)
        await db.flush()

        return self._to_info(record), destination

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        name = Path(filename).name.strip() or "document.pdf"
        name = _UNSAFE_FILENAME.sub("_", name)
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return name[:512]

    @staticmethod
    def _to_info(row: UploadedFileRecord) -> UploadedFileInfo:
        return UploadedFileInfo(
            file_id=row.id,
            filename=row.original_filename,
            size_bytes=row.size_bytes,
            content_type=row.content_type,
            uploaded_at=row.uploaded_at,
            checksum_sha256=row.checksum_sha256,
        )
