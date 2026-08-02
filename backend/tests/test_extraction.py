"""AI medical extraction + LLM client tests."""

import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.database import init_db
from backend.services.extraction_service import ExtractionError, ExtractionService
from backend.utils.config import Settings, get_settings
from backend.utils.llm import LLMClient, OllamaClient, OpenAIClient, get_llm_client
from backend.utils.paths import resolve_path

SAMPLE_TEXT = """
Patient Name: Jane Doe
Hospital: City General Hospital
Doctor: Dr. Smith
Visit Date: 2024-03-15
Diagnosis: Type 2 Diabetes Mellitus, Hypertension
Medicines: Metformin 500mg twice daily for 30 days; Lisinopril 10mg once daily
Allergies: Penicillin
Labs: HbA1c 7.1 %, Creatinine 0.9 mg/dL
Vitals: BP 130/85 mmHg, HR 78 bpm
"""

FAKE_EXTRACTION = {
    "patient_name": "Jane Doe",
    "hospital": "City General Hospital",
    "doctor": "Dr. Smith",
    "visit_date": "2024-03-15",
    "diagnosis": ["Type 2 Diabetes Mellitus", "Hypertension"],
    "medicines": [
        {
            "name": "Metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
            "duration": "30 days",
        },
        {
            "name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "once daily",
            "duration": None,
        },
    ],
    "allergies": ["Penicillin"],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "value": "7.1",
            "unit": "%",
            "reference_range": None,
            "status": None,
        }
    ],
    "vital_signs": [
        {"name": "Blood Pressure", "value": "130/85", "unit": "mmHg"},
        {"name": "Heart Rate", "value": "78", "unit": "bpm"},
    ],
}


class FakeLLM(LLMClient):
    provider_name = "fake"

    def __init__(self, content: str | None = None) -> None:
        self.content = content or json.dumps(FAKE_EXTRACTION)
        self.calls = 0

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        self.calls += 1
        return self.content


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
async def test_extraction_service_returns_structured_json() -> None:
    service = ExtractionService(settings=Settings(llm_provider="ollama"), llm=FakeLLM())
    result = await service.extract(SAMPLE_TEXT)

    assert result.data.patient_name == "Jane Doe"
    assert result.data.hospital == "City General Hospital"
    assert result.data.doctor == "Dr. Smith"
    assert result.data.visit_date == "2024-03-15"
    assert "Hypertension" in result.data.diagnosis
    assert result.data.medicines[0].dosage == "500mg"
    assert result.data.medicines[0].frequency == "twice daily"
    assert result.data.medicines[0].duration == "30 days"
    assert result.data.allergies == ["Penicillin"]
    assert result.data.lab_results[0].test_name == "HbA1c"
    assert result.data.vital_signs[0].name == "Blood Pressure"
    assert 0.0 <= result.confidence.score <= 1.0
    assert result.llm_provider == "fake"


@pytest.mark.asyncio
async def test_extraction_parses_markdown_fenced_json() -> None:
    fenced = f"```json\n{json.dumps(FAKE_EXTRACTION)}\n```"
    service = ExtractionService(llm=FakeLLM(fenced))
    result = await service.extract(SAMPLE_TEXT)
    assert result.data.patient_name == "Jane Doe"


@pytest.mark.asyncio
async def test_extraction_rejects_empty_text() -> None:
    service = ExtractionService(llm=FakeLLM())
    with pytest.raises(ExtractionError):
        await service.extract("   ")


@pytest.mark.asyncio
async def test_extraction_rejects_invalid_model_json() -> None:
    service = ExtractionService(llm=FakeLLM("not-json"))
    with pytest.raises(ExtractionError):
        await service.extract(SAMPLE_TEXT)


def test_llm_factory_openai_requires_key() -> None:
    with pytest.raises(Exception):
        get_llm_client(Settings(llm_provider="openai", openai_api_key=""))


def test_llm_factory_returns_expected_clients() -> None:
    ollama = get_llm_client(Settings(llm_provider="ollama"))
    openai = get_llm_client(Settings(llm_provider="openai", openai_api_key="sk-test"))
    assert isinstance(ollama, OllamaClient)
    assert isinstance(openai, OpenAIClient)
    assert ollama.provider_name == "ollama"
    assert openai.provider_name == "openai"


@pytest.mark.asyncio
async def test_openai_client_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OpenAIClient(Settings(llm_provider="openai", openai_api_key="sk-test"))

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers=None, json=None):
            assert url.endswith("/chat/completions")
            assert headers["Authorization"] == "Bearer sk-test"
            assert json["response_format"]["type"] == "json_object"
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    content = await client.complete(
        system_prompt="sys",
        user_prompt="user",
        json_mode=True,
    )
    assert content == '{"ok": true}'


@pytest.mark.asyncio
async def test_extract_structured_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLLM()

    def _fake_get_llm_client(settings=None):
        return fake

    monkeypatch.setattr("backend.api.routes.analysis.get_llm_client", _fake_get_llm_client)

    response = await client.post(
        "/api/v1/analysis/extract-structured",
        json={"text": SAMPLE_TEXT},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["patient_name"] == "Jane Doe"
    assert payload["data"]["medicines"][0]["name"] == "Metformin"
    assert "confidence" in payload
    assert payload["source"] == "text"
