"""Reusable document text extraction via PyMuPDF with OCR fallback.

Supports PDFs and common image formats (PNG, JPEG, WEBP, TIFF, BMP, GIF).
Images and scanned PDFs are OCR'd via RapidOCR (bundled) and/or Tesseract.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import pymupdf

from backend.utils.config import Settings, get_settings

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}

_DEFAULT_TESSDATA_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tessdata",
    r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tessdata",
    "/opt/homebrew/share/tessdata",
)


class ExtractionMethod(str, Enum):
    TEXT = "text"
    OCR = "ocr"
    EMPTY = "empty"


class PdfExtractionError(Exception):
    """Raised when a document cannot be opened or processed."""


@dataclass(slots=True)
class ExtractedPage:
    """Text extracted from a single PDF/image page."""

    page_number: int
    text: str
    method: Literal["text", "ocr", "empty"]
    char_count: int
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PdfExtractionResult:
    """Full-document extraction result (JSON-serializable)."""

    source_path: str
    page_count: int
    pages: list[ExtractedPage] = field(default_factory=list)
    full_text: str = ""
    ocr_page_numbers: list[int] = field(default_factory=list)
    text_page_numbers: list[int] = field(default_factory=list)
    empty_page_numbers: list[int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "page_count": self.page_count,
            "pages": [page.to_dict() for page in self.pages],
            "full_text": self.full_text,
            "ocr_page_numbers": self.ocr_page_numbers,
            "text_page_numbers": self.text_page_numbers,
            "empty_page_numbers": self.empty_page_numbers,
            "metadata": self.metadata,
        }


@lru_cache(maxsize=1)
def _get_rapid_ocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "rapidocr-onnxruntime is not installed. "
            "Run: pip install rapidocr-onnxruntime onnxruntime"
        ) from exc
    return RapidOCR()


def discover_tessdata_path(configured: str | None = None) -> str | None:
    if configured and Path(configured).is_dir():
        return configured
    env = (os.environ.get("TESSDATA_PREFIX") or os.environ.get("TESSDATA_PATH") or "").strip()
    if env and Path(env).is_dir():
        return env
    for candidate in _DEFAULT_TESSDATA_CANDIDATES:
        if Path(candidate).is_dir():
            return candidate
    return None


class PdfService:
    """
    Extract text from PDF and image files using PyMuPDF + OCR.

    Strategy:
      1. Images → RapidOCR directly on the file.
      2. PDF pages → selectable text first, then Tesseract via PyMuPDF, then RapidOCR on pixmap.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.min_text_chars = self.settings.pdf_min_text_chars
        self.ocr_enabled = self.settings.ocr_enabled
        self.ocr_language = self.settings.ocr_language
        self.ocr_dpi = self.settings.ocr_dpi
        self.tessdata_path = discover_tessdata_path(
            (self.settings.tessdata_path or "").strip() or None
        )

    async def extract(self, file_path: str | Path) -> PdfExtractionResult:
        """Async wrapper — runs blocking PyMuPDF/OCR work in a thread."""
        return await asyncio.to_thread(self.extract_sync, file_path)

    def extract_sync(self, file_path: str | Path) -> PdfExtractionResult:
        """Synchronously extract text from a PDF or image file."""
        path = Path(file_path)
        if not path.exists():
            raise PdfExtractionError(f"File not found: {path}")
        if not path.is_file():
            raise PdfExtractionError(f"Not a file: {path}")

        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            return self._extract_image(path)

        return self._extract_pdf(path)

    def _extract_image(self, path: Path) -> PdfExtractionResult:
        if not self.ocr_enabled:
            return PdfExtractionResult(
                source_path=str(path.resolve()),
                page_count=1,
                pages=[
                    ExtractedPage(
                        page_number=1,
                        text="",
                        method=ExtractionMethod.EMPTY.value,
                        char_count=0,
                        warning="OCR is disabled.",
                    )
                ],
                metadata={"source_kind": "image", "ocr_engine": None},
            )

        text = ""
        warning = None
        engine_used = "rapidocr"
        try:
            text = self._rapid_ocr_file(path)
        except Exception as exc:
            logger.warning("RapidOCR failed for image %s: %s", path.name, exc)
            warning = f"RapidOCR failed: {exc}"
            # Fall back to PyMuPDF + Tesseract if available.
            try:
                document = pymupdf.open(path)
                try:
                    page = document.load_page(0)
                    text = self._ocr_page_tesseract(page)
                    engine_used = "tesseract"
                    warning = None
                finally:
                    document.close()
            except Exception as tess_exc:
                warning = f"{warning}; Tesseract fallback failed: {tess_exc}"

        method = ExtractionMethod.OCR if self._has_usable_text(text) else ExtractionMethod.EMPTY
        page = ExtractedPage(
            page_number=1,
            text=text.strip(),
            method=method.value,
            char_count=len(text.strip()),
            warning=None if method == ExtractionMethod.OCR else (warning or "OCR returned no content."),
        )
        return PdfExtractionResult(
            source_path=str(path.resolve()),
            page_count=1,
            pages=[page],
            full_text=page.text,
            ocr_page_numbers=[1] if method == ExtractionMethod.OCR else [],
            empty_page_numbers=[1] if method == ExtractionMethod.EMPTY else [],
            metadata={
                "source_kind": "image",
                "ocr_engine": engine_used if method == ExtractionMethod.OCR else None,
                "tessdata_path": self.tessdata_path,
            },
        )

    def _extract_pdf(self, path: Path) -> PdfExtractionResult:
        try:
            document = pymupdf.open(path)
        except Exception as exc:
            raise PdfExtractionError(f"Unable to open file: {path}") from exc

        try:
            pages: list[ExtractedPage] = []
            for index in range(document.page_count):
                page = document.load_page(index)
                pages.append(self._extract_pdf_page(page, page_number=index + 1))

            full_text = "\n\n".join(page.text for page in pages if page.text.strip()).strip()
            metadata = self._document_metadata(document)
            metadata["source_kind"] = "pdf"
            metadata["tessdata_path"] = self.tessdata_path

            return PdfExtractionResult(
                source_path=str(path.resolve()),
                page_count=document.page_count,
                pages=pages,
                full_text=full_text,
                ocr_page_numbers=[p.page_number for p in pages if p.method == "ocr"],
                text_page_numbers=[p.page_number for p in pages if p.method == "text"],
                empty_page_numbers=[p.page_number for p in pages if p.method == "empty"],
                metadata=metadata,
            )
        finally:
            document.close()

    async def extract_text(self, file_path: str) -> str:
        """Return concatenated full text (compatibility helper)."""
        result = await self.extract(file_path)
        return result.full_text

    async def extract_pages(self, file_path: str) -> list[str]:
        """Return a list of per-page text strings (compatibility helper)."""
        result = await self.extract(file_path)
        return [page.text for page in result.pages]

    def _extract_pdf_page(self, page: pymupdf.Page, page_number: int) -> ExtractedPage:
        native = (page.get_text("text") or "").strip()
        if self._has_usable_text(native):
            return ExtractedPage(
                page_number=page_number,
                text=native,
                method=ExtractionMethod.TEXT.value,
                char_count=len(native),
            )

        if not self.ocr_enabled:
            return ExtractedPage(
                page_number=page_number,
                text="",
                method=ExtractionMethod.EMPTY.value,
                char_count=0,
                warning="No selectable text and OCR is disabled.",
            )

        warnings: list[str] = []
        ocr_text = ""

        try:
            ocr_text = self._ocr_page_tesseract(page)
        except Exception as exc:
            logger.warning("Tesseract OCR failed on page %s: %s", page_number, exc)
            warnings.append(f"Tesseract: {exc}")

        if not self._has_usable_text(ocr_text):
            try:
                ocr_text = self._rapid_ocr_pixmap(page)
            except Exception as exc:
                logger.warning("RapidOCR failed on page %s: %s", page_number, exc)
                warnings.append(f"RapidOCR: {exc}")

        if self._has_usable_text(ocr_text):
            return ExtractedPage(
                page_number=page_number,
                text=ocr_text.strip(),
                method=ExtractionMethod.OCR.value,
                char_count=len(ocr_text.strip()),
            )

        return ExtractedPage(
            page_number=page_number,
            text="",
            method=ExtractionMethod.EMPTY.value,
            char_count=0,
            warning="; ".join(warnings) if warnings else "OCR returned no content.",
        )

    def _ocr_page_tesseract(self, page: pymupdf.Page) -> str:
        kwargs: dict[str, Any] = {
            "language": self.ocr_language,
            "dpi": self.ocr_dpi,
            "full": True,
        }
        if self.tessdata_path:
            kwargs["tessdata"] = self.tessdata_path

        # Ensure tesseract binary can be found on Windows installs.
        tess_bin = Path(r"C:\Program Files\Tesseract-OCR")
        if tess_bin.is_dir():
            os.environ["PATH"] = str(tess_bin) + os.pathsep + os.environ.get("PATH", "")

        textpage = page.get_textpage_ocr(**kwargs)
        return page.get_text("text", textpage=textpage) or ""

    def _rapid_ocr_file(self, path: Path) -> str:
        engine = _get_rapid_ocr()
        result, _elapse = engine(str(path))
        if not result:
            return ""
        return "\n".join(str(line[1]).strip() for line in result if line and line[1]).strip()

    def _rapid_ocr_pixmap(self, page: pymupdf.Page) -> str:
        scale = max(self.ocr_dpi / 72.0, 1.0)
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pix.tobytes("png")
        engine = _get_rapid_ocr()
        result, _elapse = engine(png_bytes)
        if not result:
            return ""
        return "\n".join(str(line[1]).strip() for line in result if line and line[1]).strip()

    def _has_usable_text(self, text: str) -> bool:
        return len(text.strip()) >= self.min_text_chars

    @staticmethod
    def _document_metadata(document: pymupdf.Document) -> dict[str, Any]:
        meta = document.metadata or {}
        return {
            "title": meta.get("title") or None,
            "author": meta.get("author") or None,
            "subject": meta.get("subject") or None,
            "creator": meta.get("creator") or None,
            "producer": meta.get("producer") or None,
            "format": getattr(document, "name", None) or meta.get("format"),
            "page_count": document.page_count,
            "is_encrypted": bool(document.is_encrypted),
            "is_pdf": bool(document.is_pdf),
        }
