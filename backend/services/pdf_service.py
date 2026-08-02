"""Reusable PDF text extraction via PyMuPDF with OCR fallback."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pymupdf

from backend.utils.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ExtractionMethod(str, Enum):
    TEXT = "text"
    OCR = "ocr"
    EMPTY = "empty"


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be opened or processed."""


@dataclass(slots=True)
class ExtractedPage:
    """Text extracted from a single PDF page."""

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


class PdfService:
    """
    Extract text from PDF files using PyMuPDF.

    Strategy per page:
      1. Try selectable text via ``page.get_text()``.
      2. If the page has no usable selectable text, OCR via ``page.get_textpage_ocr()``.
      3. If OCR is disabled/unavailable, record an empty page with a warning.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.min_text_chars = self.settings.pdf_min_text_chars
        self.ocr_enabled = self.settings.ocr_enabled
        self.ocr_language = self.settings.ocr_language
        self.ocr_dpi = self.settings.ocr_dpi
        self.tessdata_path = (self.settings.tessdata_path or "").strip() or None

    async def extract(self, file_path: str | Path) -> PdfExtractionResult:
        """Async wrapper — runs blocking PyMuPDF work in a thread."""
        return await asyncio.to_thread(self.extract_sync, file_path)

    def extract_sync(self, file_path: str | Path) -> PdfExtractionResult:
        """Synchronously extract text from every page of a PDF."""
        path = Path(file_path)
        if not path.exists():
            raise PdfExtractionError(f"PDF not found: {path}")
        if not path.is_file():
            raise PdfExtractionError(f"Not a file: {path}")

        try:
            document = pymupdf.open(path)
        except Exception as exc:  # pymupdf raises various errors for corrupt files
            raise PdfExtractionError(f"Unable to open PDF: {path}") from exc

        try:
            pages: list[ExtractedPage] = []
            for index in range(document.page_count):
                page = document.load_page(index)
                pages.append(self._extract_page(page, page_number=index + 1))

            full_text = "\n\n".join(
                page.text for page in pages if page.text.strip()
            ).strip()

            result = PdfExtractionResult(
                source_path=str(path.resolve()),
                page_count=document.page_count,
                pages=pages,
                full_text=full_text,
                ocr_page_numbers=[p.page_number for p in pages if p.method == "ocr"],
                text_page_numbers=[p.page_number for p in pages if p.method == "text"],
                empty_page_numbers=[p.page_number for p in pages if p.method == "empty"],
                metadata=self._document_metadata(document),
            )
            return result
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

    def _extract_page(self, page: pymupdf.Page, page_number: int) -> ExtractedPage:
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

        try:
            ocr_text = self._ocr_page(page)
        except Exception as exc:
            logger.warning("OCR failed on page %s: %s", page_number, exc)
            return ExtractedPage(
                page_number=page_number,
                text="",
                method=ExtractionMethod.EMPTY.value,
                char_count=0,
                warning=f"OCR failed: {exc}",
            )

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
            warning="No selectable text and OCR returned no content.",
        )

    def _ocr_page(self, page: pymupdf.Page) -> str:
        """
        OCR a page using PyMuPDF's Tesseract integration.

        Requires Tesseract language data (tessdata). Configure via
        ``TESSDATA_PATH`` / ``OCR_LANGUAGE`` settings when auto-discovery fails.
        """
        kwargs: dict[str, Any] = {
            "language": self.ocr_language,
            "dpi": self.ocr_dpi,
            "full": True,
        }
        if self.tessdata_path:
            kwargs["tessdata"] = self.tessdata_path

        textpage = page.get_textpage_ocr(**kwargs)
        return page.get_text("text", textpage=textpage) or ""

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
