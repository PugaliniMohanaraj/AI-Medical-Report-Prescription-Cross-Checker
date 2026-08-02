"""PDF upload endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.database import init_db
from backend.utils.config import get_settings
from backend.utils.paths import resolve_path

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000068 00000 n 
0000000125 00000 n 
trailer<< /Size 4 /Root 1 0 R >>
startxref
203
%%EOF
"""


@pytest.fixture
async def client():
    settings = get_settings()
    resolve_path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    resolve_path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_upload_multiple_pdfs(client: AsyncClient) -> None:
    files = [
        ("files", ("report-a.pdf", MINIMAL_PDF, "application/pdf")),
        ("files", ("report-b.pdf", MINIMAL_PDF, "application/pdf")),
    ]
    response = await client.post("/api/v1/uploads", files=files)

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["files"]) == 2
    assert all(item["filename"].endswith(".pdf") for item in payload["files"])

    listed = await client.get("/api/v1/uploads")
    assert listed.status_code == 200
    assert listed.json()["count"] >= 2

    file_id = payload["files"][0]["file_id"]
    detail = await client.get(f"/api/v1/uploads/{file_id}")
    assert detail.status_code == 200
    assert detail.json()["file_id"] == file_id

    stored = resolve_path(get_settings().upload_dir) / f"{file_id}.pdf"
    assert stored.exists()

    deleted = await client.delete(f"/api/v1/uploads/{file_id}")
    assert deleted.status_code == 204
    assert not stored.exists()

    # cleanup second file
    second_id = payload["files"][1]["file_id"]
    await client.delete(f"/api/v1/uploads/{second_id}")


@pytest.mark.asyncio
async def test_reject_non_pdf(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "errors" in detail
    assert any("pdf" in err.lower() for err in detail["errors"])


@pytest.mark.asyncio
async def test_reject_empty_pdf_named_file(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files=[("files", ("empty.pdf", b"", "application/pdf"))],
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reject_fake_pdf_extension(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files=[("files", ("fake.pdf", b"not-a-real-pdf", "application/pdf"))],
    )
    assert response.status_code == 400
    assert any("valid PDF" in err for err in response.json()["detail"]["errors"])
