"""RAG pipeline: ingest → embed → retrieve → generate (Llama/OpenAI)."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any

from backend.models.schemas import ConfidenceScore, RagQueryResponse, RagSource
from backend.rag.chunking import split_text
from backend.rag.embeddings import EmbeddingService
from backend.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from backend.rag.retriever import Retriever
from backend.rag.vectorstore import RetrievedChunk, VectorStore
from backend.utils.config import Settings, get_settings
from backend.utils.llm import LLMClient, LLMError, get_llm_client

logger = logging.getLogger(__name__)


class RagError(Exception):
    """Raised when RAG ingest/query fails."""


class RagPipeline:
    """
    Retrieval-Augmented Generation pipeline.

    Stages:
      1. Chunk documents (LangChain splitter when available)
      2. Embed with BGE / hashing fallback
      3. Persist/query via ChromaDB or in-memory store
      4. Retrieve top-k context
      5. Generate answer via OpenAI or local Llama (Ollama)
      6. Attach confidence + supporting references
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        embeddings: EmbeddingService | None = None,
        vectorstore: VectorStore | None = None,
        llm: LLMClient | None = None,
        force_memory: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings or EmbeddingService(
            self.settings,
            force_hash=force_memory or self.settings.rag_vector_backend == "memory",
        )
        self.vectorstore = vectorstore or VectorStore(
            self.settings,
            self.embeddings,
            force_memory=force_memory,
        )
        self.retriever = Retriever(
            self.vectorstore,
            default_top_k=self.settings.rag_default_top_k,
        )
        self._llm = llm

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = get_llm_client(self.settings)
        return self._llm

    async def ingest(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Ingest documents into the vector store.

        Each document dict supports:
          - content / text (required)
          - document_id / id
          - metadata (optional dict)
          - title / source / patient_id / visit_date (copied into metadata)
        """
        return await asyncio.to_thread(self.ingest_sync, documents)

    def ingest_sync(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        if not documents:
            raise RagError("No documents provided for ingest")

        chunks_to_add: list[dict[str, Any]] = []
        source_count = 0

        for doc in documents:
            content = (doc.get("content") or doc.get("text") or "").strip()
            if not content:
                continue
            source_count += 1
            document_id = str(doc.get("document_id") or doc.get("id") or uuid.uuid4())
            metadata = {
                **dict(doc.get("metadata") or {}),
                "document_id": document_id,
                "title": doc.get("title") or doc.get("filename") or document_id,
                "source": doc.get("source") or "manual",
            }
            for key in ("patient_id", "visit_date", "file_id", "visit_id"):
                if doc.get(key) is not None:
                    metadata[key] = doc[key]

            for chunk in split_text(
                content,
                chunk_size=self.settings.rag_chunk_size,
                chunk_overlap=self.settings.rag_chunk_overlap,
                metadata=metadata,
            ):
                chunk_id = f"{document_id}:::{chunk.metadata.get('chunk_index', 0)}"
                chunks_to_add.append(
                    {
                        "id": chunk_id,
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                    }
                )

        if not chunks_to_add:
            raise RagError("Documents contained no ingestible text")

        ids = self.vectorstore.add_documents(chunks_to_add)
        return {
            "documents_ingested": source_count,
            "chunks_indexed": len(ids),
            "backend": self.vectorstore.backend,
            "embedding_backend": self.embeddings.backend,
            "chunk_ids": ids,
        }

    async def query(
        self,
        question: str,
        *,
        top_k: int | None = None,
        patient_id: str | None = None,
    ) -> RagQueryResponse:
        cleaned = (question or "").strip()
        if not cleaned:
            raise RagError("Question is empty")

        k = top_k or self.settings.rag_default_top_k
        retrieved = await asyncio.to_thread(self.retriever.retrieve, cleaned, k)

        if patient_id:
            retrieved = [
                chunk
                for chunk in retrieved
                if str(chunk.metadata.get("patient_id") or "") in {"", patient_id}
                or chunk.metadata.get("patient_id") == patient_id
            ] or retrieved

        contexts = [chunk.content for chunk in retrieved]
        sources = [
            RagSource(
                document_id=str(chunk.metadata.get("document_id") or chunk.document_id),
                excerpt=_excerpt(chunk.content),
                score=chunk.score,
                title=str(chunk.metadata.get("title") or "") or None,
                source=str(chunk.metadata.get("source") or "") or None,
                metadata={
                    key: value
                    for key, value in chunk.metadata.items()
                    if key not in {"chunk_index"} and value is not None
                },
            )
            for chunk in retrieved
        ]

        if not retrieved:
            return RagQueryResponse(
                answer=(
                    "I could not find supporting documents for that question. "
                    "Ingest medical reports into the RAG index first, then try again."
                ),
                confidence=ConfidenceScore(
                    score=0.15,
                    rationale="No retrieved context chunks were available.",
                ),
                sources=[],
                llm_provider=None,
                retrieval_backend=self.vectorstore.backend,
            )

        try:
            answer = await self.llm.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(cleaned, contexts),
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
                json_mode=False,
            )
            provider = self.llm.provider_name
        except LLMError as exc:
            logger.warning("RAG LLM failed (%s); using extractive fallback.", exc)
            answer = _extractive_fallback(cleaned, retrieved)
            provider = "extractive_fallback"

        confidence = _estimate_confidence(cleaned, answer, retrieved)
        return RagQueryResponse(
            answer=answer.strip(),
            confidence=confidence,
            sources=sources,
            llm_provider=provider,
            retrieval_backend=self.vectorstore.backend,
        )


def _excerpt(text: str, limit: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _estimate_confidence(
    question: str,
    answer: str,
    retrieved: list[RetrievedChunk],
) -> ConfidenceScore:
    if not retrieved:
        return ConfidenceScore(score=0.15, rationale="No supporting documents retrieved.")

    top_score = max(chunk.score for chunk in retrieved)
    mean_score = sum(chunk.score for chunk in retrieved) / len(retrieved)
    uncertain = any(
        phrase in answer.lower()
        for phrase in (
            "cannot find",
            "not enough",
            "insufficient",
            "do not have",
            "don't have",
            "unable to determine",
            "no information",
        )
    )
    overlap = _token_overlap(question, " ".join(chunk.content for chunk in retrieved[:3]))
    score = 0.25 + (0.45 * max(0.0, top_score)) + (0.2 * max(0.0, mean_score)) + (0.1 * overlap)
    if uncertain:
        score *= 0.55
    score = round(min(0.98, max(0.05, score)), 3)
    return ConfidenceScore(
        score=score,
        rationale=(
            f"Retrieved {len(retrieved)} chunk(s); top similarity={top_score:.3f}; "
            f"mean={mean_score:.3f}; question-context overlap={overlap:.2f}."
        ),
    )


def _token_overlap(left: str, right: str) -> float:
    a = set(re.findall(r"[a-z0-9]+", left.lower()))
    b = set(re.findall(r"[a-z0-9]+", right.lower()))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def _extractive_fallback(question: str, retrieved: list[RetrievedChunk]) -> str:
    """Deterministic answer when the LLM is unavailable."""
    q = question.lower()
    joined = "\n".join(chunk.content for chunk in retrieved[:3])

    if "conflict" in q or "interaction" in q:
        return (
            "Based on retrieved notes, review the cited excerpts for medicine conflicts "
            f"or interactions.\n\nMost relevant excerpt: {_excerpt(retrieved[0].content, 360)}"
        )
    if "changed" in q or "between visits" in q or "trend" in q:
        return (
            "Retrieved visit excerpts suggest changes across encounters. "
            f"Compare the following evidence:\n{_excerpt(joined, 500)}"
        )
    if "diagnos" in q or "diabetes" in q or "when" in q:
        return (
            "From the supporting documents, the closest evidence is:\n"
            f"{_excerpt(retrieved[0].content, 420)}"
        )
    return (
        "Here is the most relevant evidence from the medical documents:\n"
        f"{_excerpt(retrieved[0].content, 420)}"
    )
