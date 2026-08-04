"""Upload storage and validation for PDFs and common image formats."""

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

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
    "image/tif",
    "image/bmp",
    "image/x-ms-bmp",
    "image/gif",
}

EXTENSION_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}

_UNSAFE_FILENAME = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)


class UploadValidationError(Exception):
    """Raised when one or more uploaded files fail validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class UploadService:
    """Validate, persist, and track uploaded PDF and image files."""

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
        prepared: list[tuple[UploadFile, bytes, str, str]] = []
        errors: list[str] = []

        for index, upload in enumerate(files, start=1):
            label = upload.filename or f"file_{index}"
            try:
                raw = await upload.read()
                extension = self._validate_file(label, upload.content_type, raw)
                prepared.append((upload, raw, label, extension))
            except UploadValidationError as exc:
                errors.extend(exc.errors)
            finally:
                await upload.close()

        if errors:
            raise UploadValidationError(errors)

        saved: list[UploadedFileInfo] = []
        written_paths: list[Path] = []

        try:
            for upload, raw, label, extension in prepared:
                info, path = await self._persist_one(upload, raw, label, extension, db)
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

    async def get_stored_path(self, file_id: str, db: AsyncSession) -> Path | None:
        """Resolve the on-disk path for an uploaded file (PDF or image)."""
        row = await db.get(UploadedFileRecord, file_id)
        if row is None:
            return None
        return self.upload_dir / row.stored_filename

    async def delete_upload(self, file_id: str, db: AsyncSession) -> bool:
        row = await db.get(UploadedFileRecord, file_id)
        if row is None:
            return False

        path = self.upload_dir / row.stored_filename
        await db.delete(row)
        await db.commit()
        path.unlink(missing_ok=True)
        return True

    def _validate_file(self, filename: str, content_type: str | None, raw: bytes) -> str:
        errors: list[str] = []
        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            errors.append(
                f"'{filename}' has unsupported type. Allowed extensions: {allowed}."
            )

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
        elif extension and not self._matches_magic(extension, raw):
            kind = "PDF" if extension == ".pdf" else "image"
            errors.append(f"'{filename}' is not a valid {kind} file.")

        if errors:
            raise UploadValidationError(errors)

        return extension

    @staticmethod
    def _matches_magic(extension: str, raw: bytes) -> bool:
        data = raw.lstrip() if extension == ".pdf" else raw
        if extension == ".pdf":
            return data.startswith(PDF_MAGIC)
        if extension == ".png":
            return raw.startswith(b"\x89PNG\r\n\x1a\n")
        if extension in {".jpg", ".jpeg"}:
            return raw.startswith(b"\xff\xd8\xff")
        if extension == ".webp":
            return len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
        if extension == ".gif":
            return raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a")
        if extension == ".bmp":
            return raw.startswith(b"BM")
        if extension in {".tif", ".tiff"}:
            return raw.startswith(b"II*\x00") or raw.startswith(b"MM\x00*")
        return False

    async def _persist_one(
        self,
        upload: UploadFile,
        raw: bytes,
        label: str,
        extension: str,
        db: AsyncSession,
    ) -> tuple[UploadedFileInfo, Path]:
        file_id = str(uuid.uuid4())
        safe_name = self._sanitize_filename(label, extension)
        stored_filename = f"{file_id}{extension}"
        destination = self.upload_dir / stored_filename
        checksum = hashlib.sha256(raw).hexdigest()
        uploaded_at = datetime.now(timezone.utc)
        content_type = self._resolve_content_type(extension, upload.content_type)

        async with aiofiles.open(destination, "wb") as handle:
            await handle.write(raw)

        record = UploadedFileRecord(
            id=file_id,
            original_filename=safe_name,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=len(raw),
            checksum_sha256=checksum,
            uploaded_at=uploaded_at,
        )
        db.add(record)
        await db.flush()

        return self._to_info(record), destination

    @staticmethod
    def _resolve_content_type(extension: str, content_type: str | None) -> str:
        normalized = (content_type or "").split(";")[0].strip().lower()
        if normalized and normalized != "application/octet-stream":
            if normalized == "image/jpg":
                return "image/jpeg"
            return normalized
        return EXTENSION_CONTENT_TYPES.get(extension, "application/octet-stream")

    @staticmethod
    def _sanitize_filename(filename: str, extension: str) -> str:
        name = Path(filename).name.strip() or f"document{extension}"
        name = _UNSAFE_FILENAME.sub("_", name)
        if Path(name).suffix.lower() != extension:
            stem = Path(name).stem or "document"
            name = f"{stem}{extension}"
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
