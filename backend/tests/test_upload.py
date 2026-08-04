"""Upload endpoint tests for PDFs and images."""

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

# 1x1 PNG
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal JPEG (JFIF)
MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a"
    b"\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00"
    b"\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01"
    b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01"
    b"}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1"
    b"\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84"
    b"\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6"
    b"\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8"
    b"\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9"
    b"\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?"
    b"\x00\xfe\xd5\xd5\x00\xff\xd9"
)


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
async def test_upload_png_and_jpeg(client: AsyncClient) -> None:
    files = [
        ("files", ("scan.png", MINIMAL_PNG, "image/png")),
        ("files", ("photo.jpg", MINIMAL_JPEG, "image/jpeg")),
    ]
    response = await client.post("/api/v1/uploads", files=files)

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["count"] == 2
    assert payload["files"][0]["content_type"] == "image/png"
    assert payload["files"][1]["content_type"] == "image/jpeg"

    png_id = payload["files"][0]["file_id"]
    jpg_id = payload["files"][1]["file_id"]
    assert (resolve_path(get_settings().upload_dir) / f"{png_id}.png").exists()
    assert (resolve_path(get_settings().upload_dir) / f"{jpg_id}.jpg").exists()

    await client.delete(f"/api/v1/uploads/{png_id}")
    await client.delete(f"/api/v1/uploads/{jpg_id}")


@pytest.mark.asyncio
async def test_reject_unsupported_type(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "errors" in detail
    assert any("unsupported" in err.lower() for err in detail["errors"])


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


@pytest.mark.asyncio
async def test_reject_fake_image_extension(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files=[("files", ("fake.png", b"not-a-png", "image/png"))],
    )
    assert response.status_code == 400
    assert any("valid image" in err for err in response.json()["detail"]["errors"])
