"""Lab trend analysis tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.database import init_db
from backend.models.schemas import LabResult, LabTrendRequest, LabVisitInput
from backend.services.lab_service import LabService
from backend.utils.config import Settings, get_settings
from backend.utils.llm import LLMClient
from backend.utils.paths import resolve_path


class FakeLLM(LLMClient):
    provider_name = "fake"

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        return (
            "HbA1c is rising across visits and remains above the reference range, "
            "suggesting worsening glycemic control. Creatinine is stable within limits. "
            "Recommend correlating with therapy adherence and repeating labs as clinically indicated."
        )


SAMPLE_VISITS = [
    LabVisitInput(
        visit_id="v1",
        visit_date="2024-01-10",
        labs=[
            LabResult(test_name="HbA1c", value="6.8", unit="%", reference_range="4.0-5.6"),
            LabResult(test_name="Creatinine", value="0.9", unit="mg/dL"),
            LabResult(test_name="LDL", value="110", unit="mg/dL"),
        ],
    ),
    LabVisitInput(
        visit_id="v2",
        visit_date="2024-06-15",
        labs=[
            LabResult(test_name="HbA1c", value="7.4", unit="%"),
            LabResult(test_name="Creatinine", value="0.95", unit="mg/dL"),
            LabResult(test_name="LDL", value="128", unit="mg/dL"),
        ],
    ),
    LabVisitInput(
        visit_id="v3",
        visit_date="2024-12-01",
        labs=[
            LabResult(test_name="A1C", value="8.1", unit="%"),
            LabResult(test_name="Creatinine", value="1.0", unit="mg/dL"),
            LabResult(test_name="LDL cholesterol", value="145", unit="mg/dL"),
        ],
    ),
]


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
async def test_lab_trends_compare_across_visits() -> None:
    service = LabService(settings=Settings(lab_ai_explanations_enabled=False))
    result = await service.analyze(
        LabTrendRequest(patient_id="p1", visits=SAMPLE_VISITS, include_ai_explanation=False)
    )

    assert result.visit_count == 3
    names = {s.test_name.lower() for s in result.series}
    assert any("hba1c" in n or "a1c" in n for n in names)
    assert result.charts
    assert all(len(chart.data) >= 2 for chart in result.charts if "a1c" in chart.test_name.lower())


@pytest.mark.asyncio
async def test_abnormal_trends_highlighted() -> None:
    service = LabService(settings=Settings(lab_ai_explanations_enabled=False))
    result = await service.analyze(
        LabTrendRequest(visits=SAMPLE_VISITS, include_ai_explanation=False)
    )

    assert result.abnormal_trends
    hba1c = next(s for s in result.series if "a1c" in s.test_name.lower())
    assert hba1c.is_abnormal_trend is True
    assert hba1c.direction == "rising"
    assert hba1c.severity in {"Low", "Medium", "High"}
    assert hba1c.points[-1].is_abnormal is True


@pytest.mark.asyncio
async def test_ai_explanation_generated() -> None:
    service = LabService(
        settings=Settings(lab_ai_explanations_enabled=True),
        llm=FakeLLM(),
    )
    result = await service.analyze(LabTrendRequest(visits=SAMPLE_VISITS))
    assert result.ai_explanation
    assert "HbA1c" in result.ai_explanation or "glycemic" in result.ai_explanation.lower()
    assert result.llm_provider == "fake"
    assert result.confidence.score > 0


@pytest.mark.asyncio
async def test_labs_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.services.lab_service.get_llm_client",
        lambda settings=None: FakeLLM(),
    )

    response = await client.post(
        "/api/v1/analysis/labs",
        json={
            "patient_id": "demo",
            "include_ai_explanation": True,
            "visits": [
                {
                    "visit_id": "v1",
                    "visit_date": "2024-01-10",
                    "labs": [{"test_name": "HbA1c", "value": "6.8", "unit": "%"}],
                },
                {
                    "visit_id": "v2",
                    "visit_date": "2024-08-10",
                    "labs": [{"test_name": "HbA1c", "value": "7.9", "unit": "%"}],
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["charts"]
    assert payload["ai_explanation"]
    assert payload["abnormal_trends"]


@pytest.mark.asyncio
async def test_labs_endpoint_requires_visits(client: AsyncClient) -> None:
    response = await client.post("/api/v1/analysis/labs", json={"visits": []})
    assert response.status_code == 400
