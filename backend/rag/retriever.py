"""Retriever wrapper around the vector store."""

from __future__ import annotations

from backend.rag.vectorstore import RetrievedChunk, VectorStore


class Retriever:
    """Thin retrieval layer used by the RAG pipeline."""

    def __init__(self, vectorstore: VectorStore, *, default_top_k: int = 5) -> None:
        self.vectorstore = vectorstore
        self.default_top_k = default_top_k

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        k = top_k or self.default_top_k
        return self.vectorstore.similarity_search(query, top_k=k)

    # LangChain-style alias
    def get_relevant_documents(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        return self.retrieve(query, top_k=top_k)
