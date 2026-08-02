"""Text chunking helpers for RAG ingest (LangChain when available)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TextChunk:
    content: str
    metadata: dict[str, Any]


def split_text(
    text: str,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks.

    Uses LangChain ``RecursiveCharacterTextSplitter`` when installed; otherwise
    falls back to a simple paragraph/sentence-aware splitter.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    base_meta = dict(metadata or {})

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        parts = splitter.split_text(cleaned)
        return [
            TextChunk(content=part, metadata={**base_meta, "chunk_index": index})
            for index, part in enumerate(parts)
            if part.strip()
        ]
    except ImportError:
        return _simple_split(cleaned, chunk_size, chunk_overlap, base_meta)


def _simple_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    base_meta: dict[str, Any],
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            # Prefer breaking on whitespace.
            pivot = text.rfind(" ", start, end)
            if pivot > start + chunk_size // 3:
                end = pivot
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                TextChunk(content=piece, metadata={**base_meta, "chunk_index": index})
            )
            index += 1
        if end >= length:
            break
        start = max(0, end - chunk_overlap)
    return chunks
