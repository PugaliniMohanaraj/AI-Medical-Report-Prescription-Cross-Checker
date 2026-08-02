# Architecture Overview

## Goals

Production-ready **AI Medical Report & Prescription Cross-Checker** for competition use:
modular, scalable, clean architecture, with deferred business logic in this scaffold phase.

## High-level diagram

```
┌─────────────────────────────┐
│  React 19 + Vite Frontend   │
│  Tailwind · Router · Axios  │
│  Recharts (dashboard)       │
└──────────────┬──────────────┘
               │ HTTPS / REST
               ▼
┌─────────────────────────────┐
│  FastAPI Backend            │
│  api/ → services/ → rag/    │
└───┬───────────┬─────────┬───┘
    │           │         │
    ▼           ▼         ▼
 SQLite     ChromaDB   LLM Provider
 (meta)     (vectors)  Ollama | OpenAI
```

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| API | `backend/api` | HTTP routes, deps, request validation |
| Models | `backend/models` | Pydantic schemas + SQLAlchemy metadata |
| Services | `backend/services` | PDF, extraction, timeline, conflicts, labs |
| RAG | `backend/rag` | Embeddings, vector store, pipeline |
| Utils | `backend/utils` | Settings, LLM factory |
| UI | `frontend/src` | Pages, components, API client |

## LLM switching

`LLM_PROVIDER=ollama|openai` in `backend/.env` selects the provider via `backend/utils/llm.py`.
Embeddings default to `BAAI/bge-small-en-v1.5`.

## Deployment targets

- Frontend → Vercel (`frontend/`)
- Backend → Render (`backend/` + Docker or native Uvicorn)

## Planned feature pipeline (not implemented yet)

1. Multi-PDF upload → `PdfService`
2. Text → structured JSON → `ExtractionService`
3. Visit merge → `TimelineService`
4. Conflicts → `ConflictService`
5. Lab trends → `LabService`
6. Follow-up Q&A → `RagPipeline` + confidence scores
