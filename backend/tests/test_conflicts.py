"""Prescription conflict analysis tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.database import init_db
from backend.models.schemas import Medicine
from backend.services.conflict_service import ConflictService
from backend.utils.config import get_settings
from backend.utils.paths import resolve_path


@pytest.fixture
def service() -> ConflictService:
    return ConflictService()


@pytest.fixture
async def client():
    cfg = get_settings()
    resolve_path(cfg.upload_dir).mkdir(parents=True, exist_ok=True)
    resolve_path(cfg.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_detect_duplicates(service: ConflictService) -> None:
    result = await service.analyze(
        [
            Medicine(name="Metformin", dosage="500mg", frequency="BID"),
            Medicine(name="Glucophage", dosage="500mg", frequency="BID"),
        ]
    )
    assert any(f.type == "duplicate" for f in result.findings)
    dupes = [f for f in result.findings if f.type == "duplicate"]
    assert dupes[0].severity in {"Low", "Medium", "High"}
    assert dupes[0].explanation
    assert "metformin" in dupes[0].title.lower()


@pytest.mark.asyncio
async def test_detect_dosage_conflicts(service: ConflictService) -> None:
    result = await service.analyze(
        [
            Medicine(name="Atorvastatin", dosage="10mg", frequency="once daily"),
            Medicine(name="Lipitor", dosage="40mg", frequency="once daily"),
        ]
    )
    dosage = [f for f in result.findings if f.type == "dosage_conflict"]
    assert dosage
    assert dosage[0].severity == "High"
    assert "different dosing" in dosage[0].explanation.lower() or "conflict" in dosage[0].explanation.lower()


@pytest.mark.asyncio
async def test_detect_allergy_conflicts(service: ConflictService) -> None:
    result = await service.analyze(
        [Medicine(name="Amoxicillin", dosage="500mg")],
        allergies=["Penicillin"],
    )
    allergy = [f for f in result.findings if f.type == "allergy_conflict"]
    assert allergy
    assert allergy[0].severity == "High"
    assert "penicillin" in allergy[0].explanation.lower()
    assert allergy[0].related_allergies == ["Penicillin"]


@pytest.mark.asyncio
async def test_detect_interactions(service: ConflictService) -> None:
    result = await service.analyze(
        [
            Medicine(name="Warfarin", dosage="5mg"),
            Medicine(name="Aspirin", dosage="81mg"),
        ]
    )
    interactions = [f for f in result.findings if f.type == "interaction"]
    assert interactions
    assert interactions[0].severity == "High"
    assert "bleed" in interactions[0].explanation.lower()


@pytest.mark.asyncio
async def test_severity_summary_counts(service: ConflictService) -> None:
    result = await service.analyze(
        [
            Medicine(name="Warfarin", dosage="5mg"),
            Medicine(name="Aspirin", dosage="81mg"),
            Medicine(name="Amoxicillin", dosage="500mg"),
            Medicine(name="Amoxicillin", dosage="875mg"),
        ],
        allergies=["Penicillin"],
    )
    assert result.summary.total == len(result.findings)
    assert result.summary.high + result.summary.medium + result.summary.low == result.summary.total
    assert result.summary.total >= 3


@pytest.mark.asyncio
async def test_prescription_endpoint(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/analysis/prescription",
        json={
            "medicines": [
                {"name": "Warfarin", "dosage": "5mg", "frequency": "daily"},
                {"name": "Ibuprofen", "dosage": "400mg", "frequency": "TID"},
                {"name": "Amoxicillin", "dosage": "500mg"},
            ],
            "allergies": ["Penicillin"],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    types = {f["type"] for f in payload["findings"]}
    assert "interaction" in types
    assert "allergy_conflict" in types
    for finding in payload["findings"]:
        assert finding["severity"] in {"Low", "Medium", "High"}
        assert finding["explanation"]
        assert finding["title"]


@pytest.mark.asyncio
async def test_prescription_endpoint_requires_medicines(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/analysis/prescription",
        json={"medicines": [], "allergies": []},
    )
    assert response.status_code == 400
