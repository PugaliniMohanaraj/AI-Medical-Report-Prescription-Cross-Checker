"""RAG pipeline tests (in-memory vector store + fake LLM)."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models.database import init_db
from backend.rag.pipeline import RagPipeline
from backend.utils.config import Settings, get_settings
from backend.utils.llm import LLMClient
from backend.utils.paths import resolve_path

CORPUS = [
    {
        "document_id": "visit-1",
        "title": "Visit 2023-02-10",
        "patient_id": "p1",
        "visit_date": "2023-02-10",
        "content": (
            "Patient Jane Doe diagnosed with Type 2 Diabetes Mellitus on 2023-02-10 "
            "at City General Hospital. Started Metformin 500mg twice daily."
        ),
    },
    {
        "document_id": "visit-2",
        "title": "Visit 2024-06-15",
        "patient_id": "p1",
        "visit_date": "2024-06-15",
        "content": (
            "Follow-up visit 2024-06-15. HbA1c rose from 6.8% to 7.4%. "
            "Added Lisinopril 10mg daily for hypertension. "
            "Allergy: Penicillin. Warning: possible ACE inhibitor and NSAID interaction risk if ibuprofen used."
        ),
    },
    {
        "document_id": "rx-check",
        "title": "Prescription analysis",
        "patient_id": "p1",
        "content": (
            "Medicine conflict finding: High severity interaction between Warfarin and Aspirin "
            "due to increased bleeding risk. Allergy conflict: Amoxicillin with Penicillin allergy."
        ),
    },
]


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
        question_line = ""
        for line in user_prompt.splitlines():
            if line.lower().startswith("question:"):
                question_line = line.split(":", 1)[1].strip().lower()
                break
        lower = question_line or user_prompt.lower()

        if "conflict" in lower or "interaction" in lower:
            return (
                "Yes. Supporting documents report a high-severity Warfarin + Aspirin interaction "
                "and an Amoxicillin allergy conflict with Penicillin."
            )
        if "changed" in lower or "between visits" in lower:
            return (
                "Between 2023-02-10 and 2024-06-15, HbA1c rose from 6.8% to 7.4% and "
                "Lisinopril was added for hypertension."
            )
        if "diabetes" in lower or "diagnos" in lower or "when" in lower:
            return "Diabetes was diagnosed on 2023-02-10 according to the visit note."
        return "Based on the supporting documents, please see the cited excerpts."


@pytest.fixture
def pipeline() -> RagPipeline:
    settings = Settings(rag_vector_backend="memory", llm_provider="ollama")
    pipe = RagPipeline(settings=settings, llm=FakeLLM(), force_memory=True)
    pipe.ingest_sync(CORPUS)
    return pipe


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
async def test_rag_diabetes_diagnosis_question(pipeline: RagPipeline) -> None:
    result = await pipeline.query("When was diabetes diagnosed?")
    assert "2023-02-10" in result.answer
    assert result.sources
    assert result.confidence.score > 0.2
    assert result.sources[0].excerpt


@pytest.mark.asyncio
async def test_rag_medicine_conflict_question(pipeline: RagPipeline) -> None:
    result = await pipeline.query("Did any medicine conflict?")
    assert "warfarin" in result.answer.lower() or "interaction" in result.answer.lower()
    assert any("conflict" in (s.excerpt.lower() + s.document_id.lower()) for s in result.sources) or result.sources


@pytest.mark.asyncio
async def test_rag_between_visits_question(pipeline: RagPipeline) -> None:
    result = await pipeline.query("What changed between visits?")
    assert "hba1c" in result.answer.lower() or "7.4" in result.answer
    assert result.retrieval_backend in {"memory", "chroma"}
    assert result.llm_provider == "fake"


@pytest.mark.asyncio
async def test_rag_ingest_and_query_endpoints(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(rag_vector_backend="memory")
    pipe = RagPipeline(settings=settings, llm=FakeLLM(), force_memory=True)

    import backend.api.routes.rag as rag_routes

    monkeypatch.setattr(rag_routes, "_pipeline", pipe)

    ingest = await client.post(
        "/api/v1/rag/ingest",
        json={"documents": CORPUS, "patient_id": "p1"},
    )
    assert ingest.status_code == 201, ingest.text
    assert ingest.json()["chunks_indexed"] >= 3

    query = await client.post(
        "/api/v1/rag/query",
        json={"question": "When was diabetes diagnosed?", "top_k": 3},
    )
    assert query.status_code == 200, query.text
    payload = query.json()
    assert payload["answer"]
    assert payload["confidence"]["score"] >= 0
    assert payload["sources"]
    assert "excerpt" in payload["sources"][0]
