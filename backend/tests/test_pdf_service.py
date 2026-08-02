"""PDF text extraction service tests."""

from pathlib import Path

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.database import init_db
from backend.services.pdf_service import PdfExtractionError, PdfService
from backend.utils.config import Settings, get_settings
from backend.utils.paths import resolve_path

SAMPLE_TEXT = "Patient: Jane Doe\nMedication: Atorvastatin 10mg"


def _make_text_pdf(path: Path, text: str = SAMPLE_TEXT) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()
    return path


def _make_blank_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def settings() -> Settings:
    return Settings(ocr_enabled=True, pdf_min_text_chars=1)


@pytest.fixture
async def client():
    cfg = get_settings()
    resolve_path(cfg.upload_dir).mkdir(parents=True, exist_ok=True)
    resolve_path(cfg.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_extract_selectable_text(tmp_path: Path, settings: Settings) -> None:
    pdf_path = _make_text_pdf(tmp_path / "text.pdf")
    service = PdfService(settings)

    result = service.extract_sync(pdf_path)

    assert result.page_count == 1
    assert result.pages[0].method == "text"
    assert "Jane Doe" in result.pages[0].text
    assert "Atorvastatin" in result.full_text
    assert result.text_page_numbers == [1]
    assert result.ocr_page_numbers == []
    assert isinstance(result.to_dict()["pages"][0]["text"], str)


def test_ocr_fallback_when_no_selectable_text(tmp_path: Path, settings: Settings) -> None:
    pdf_path = _make_blank_pdf(tmp_path / "blank.pdf")
    service = PdfService(settings)

    def fake_ocr(_page: pymupdf.Page) -> str:
        return "OCR recovered lab values: HbA1c 6.2%"

    service._ocr_page = fake_ocr  # type: ignore[method-assign]

    result = service.extract_sync(pdf_path)

    assert result.pages[0].method == "ocr"
    assert "HbA1c" in result.full_text
    assert result.ocr_page_numbers == [1]


def test_empty_page_when_ocr_disabled(tmp_path: Path) -> None:
    pdf_path = _make_blank_pdf(tmp_path / "blank.pdf")
    service = PdfService(Settings(ocr_enabled=False))

    result = service.extract_sync(pdf_path)

    assert result.pages[0].method == "empty"
    assert result.pages[0].warning is not None
    assert result.empty_page_numbers == [1]


def test_missing_file_raises(tmp_path: Path, settings: Settings) -> None:
    service = PdfService(settings)
    with pytest.raises(PdfExtractionError):
        service.extract_sync(tmp_path / "missing.pdf")


@pytest.mark.asyncio
async def test_extract_text_endpoint(client: AsyncClient, tmp_path: Path) -> None:
    # Build a real PDF, upload bytes via API
    pdf_path = _make_text_pdf(tmp_path / "report.pdf")
    content = pdf_path.read_bytes()

    upload = await client.post(
        "/api/v1/uploads",
        files=[("files", ("report.pdf", content, "application/pdf"))],
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["files"][0]["file_id"]

    response = await client.post(f"/api/v1/analysis/extract-text/{file_id}")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["file_id"] == file_id
    assert payload["page_count"] >= 1
    assert "Jane Doe" in payload["full_text"]
    assert payload["pages"][0]["method"] == "text"
    assert "pages" in payload and isinstance(payload["pages"], list)

    # cleanup
    await client.delete(f"/api/v1/uploads/{file_id}")


@pytest.mark.asyncio
async def test_extract_text_not_found(client: AsyncClient) -> None:
    response = await client.post("/api/v1/analysis/extract-text/does-not-exist")
    assert response.status_code == 404
