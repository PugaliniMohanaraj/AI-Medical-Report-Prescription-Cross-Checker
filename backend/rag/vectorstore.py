"""Vector store backends: ChromaDB (preferred) and in-memory fallback."""

from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from backend.rag.embeddings import EmbeddingService
from backend.utils.config import Settings, get_settings
from backend.utils.paths import resolve_path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievedChunk:
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStoreProtocol(Protocol):
    def add_documents(self, documents: list[dict[str, Any]]) -> list[str]: ...

    def similarity_search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]: ...

    def clear(self) -> None: ...


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return float(dot / (na * nb))


class InMemoryVectorStore:
    """Cosine-similarity store used when ChromaDB is unavailable."""

    def __init__(self, embeddings: EmbeddingService) -> None:
        self.embeddings = embeddings
        self._rows: list[dict[str, Any]] = []

    def add_documents(self, documents: list[dict[str, Any]]) -> list[str]:
        ids: list[str] = []
        texts = [str(doc.get("content") or "") for doc in documents]
        vectors = self.embeddings.embed_documents(texts)
        for doc, vector in zip(documents, vectors):
            doc_id = str(doc.get("id") or uuid.uuid4())
            self._rows.append(
                {
                    "id": doc_id,
                    "content": doc.get("content") or "",
                    "metadata": dict(doc.get("metadata") or {}),
                    "embedding": vector,
                }
            )
            ids.append(doc_id)
        return ids

    def similarity_search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not self._rows:
            return []
        query_vec = self.embeddings.embed_query(query)
        scored = [
            (
                _cosine(query_vec, row["embedding"]),
                row,
            )
            for row in self._rows
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[RetrievedChunk] = []
        for score, row in scored[:top_k]:
            results.append(
                RetrievedChunk(
                    document_id=row["id"],
                    content=row["content"],
                    score=round(float(score), 4),
                    metadata=row["metadata"],
                )
            )
        return results

    def clear(self) -> None:
        self._rows.clear()


class ChromaVectorStore:
    """Persistent ChromaDB collection via langchain-chroma when available."""

    def __init__(self, settings: Settings, embeddings: EmbeddingService) -> None:
        self.settings = settings
        self.embeddings = embeddings
        self.persist_dir = resolve_path(settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = settings.chroma_collection_name

        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Chroma collection ready at %s", self.persist_dir)

    def add_documents(self, documents: list[dict[str, Any]]) -> list[str]:
        if not documents:
            return []
        ids = [str(doc.get("id") or uuid.uuid4()) for doc in documents]
        texts = [str(doc.get("content") or "") for doc in documents]
        metadatas = [self._sanitize_metadata(doc.get("metadata") or {}) for doc in documents]
        vectors = self.embeddings.embed_documents(texts)
        self._collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=vectors,
        )
        return ids

    def similarity_search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if self._collection.count() == 0:
            return []
        query_vec = self.embeddings.embed_query(query)
        raw = self._collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, max(1, self._collection.count())),
            include=["documents", "metadatas", "distances"],
        )
        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        results: list[RetrievedChunk] = []
        for doc_id, content, meta, distance in zip(ids, docs, metas, distances):
            # Chroma cosine distance ~= 1 - cosine similarity
            score = 1.0 - float(distance) if distance is not None else 0.0
            results.append(
                RetrievedChunk(
                    document_id=str(doc_id),
                    content=content or "",
                    score=round(score, 4),
                    metadata=dict(meta or {}),
                )
            )
        return results

    def clear(self) -> None:
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:  # noqa: BLE001
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[str(key)] = value
            else:
                clean[str(key)] = json.dumps(value, default=str)
        return clean


class VectorStore:
    """Facade selecting ChromaDB when possible, otherwise in-memory store."""

    def __init__(
        self,
        settings: Settings | None = None,
        embeddings: EmbeddingService | None = None,
        *,
        force_memory: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings or EmbeddingService(self.settings)
        self.persist_dir = str(resolve_path(self.settings.chroma_persist_dir))
        self._backend_name = "memory"
        self._store: VectorStoreProtocol

        if force_memory or self.settings.rag_vector_backend == "memory":
            self._store = InMemoryVectorStore(self.embeddings)
            return

        if self.settings.rag_vector_backend in {"chroma", "auto"}:
            try:
                self._store = ChromaVectorStore(self.settings, self.embeddings)
                self._backend_name = "chroma"
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("ChromaDB unavailable (%s); using in-memory vector store.", exc)

        self._store = InMemoryVectorStore(self.embeddings)

    @property
    def backend(self) -> str:
        return self._backend_name

    def add_documents(self, documents: list[dict[str, Any]]) -> list[str]:
        return self._store.add_documents(documents)

    def similarity_search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        return self._store.similarity_search(query, top_k=top_k)

    def clear(self) -> None:
        self._store.clear()
