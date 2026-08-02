"""Embedding providers for RAG (sentence-transformers / hashing fallback)."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import Sequence

from backend.utils.config import Settings, get_settings

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingService:
    """
    Produce embeddings for documents and queries.

    Preferred backend: ``sentence-transformers`` with ``BAAI/bge-small-en-v1.5``.
    Fallback: deterministic hashing embedder (no heavy deps) for local/dev/tests.
    """

    def __init__(self, settings: Settings | None = None, *, force_hash: bool = False) -> None:
        self.settings = settings or get_settings()
        self.model_name = self.settings.embedding_model
        self.dimension = self.settings.embedding_dimension
        self._backend = "hash"
        self._model = None

        if not force_hash:
            self._try_load_sentence_transformer()

    def _try_load_sentence_transformer(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._backend = "sentence_transformers"
            # Keep reported dimension in sync with model when possible.
            try:
                self.dimension = int(self._model.get_sentence_embedding_dimension())
            except Exception:  # noqa: BLE001
                pass
            logger.info("Loaded embedding model %s", self.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sentence-transformers unavailable (%s); using hashing embeddings.",
                exc,
            )
            self._backend = "hash"
            self._model = None

    @property
    def backend(self) -> str:
        return self._backend

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._backend == "sentence_transformers" and self._model is not None:
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]
        return [self._hash_embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if self._backend == "sentence_transformers" and self._model is not None:
            vector = self._model.encode([text], normalize_embeddings=True)[0]
            return vector.tolist()
        return self._hash_embed(text)

    def _hash_embed(self, text: str) -> list[float]:
        """Lightweight bag-of-tokens hashing embedder (unit-normalized)."""
        dim = self.dimension
        vec = [0.0] * dim
        tokens = _TOKEN_RE.findall((text or "").lower())
        if not tokens:
            tokens = ["empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
