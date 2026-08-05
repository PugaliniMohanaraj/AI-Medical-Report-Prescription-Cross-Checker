# Architecture Overview

## Goals

**MedCross** — AI Medical Report & Prescription Cross-Checker for competition use:
modular FastAPI + React app with real PDF/OCR ingestion, LLM extraction, rule-based
safety checks, lab trends, and RAG follow-up Q&A.

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

## End-to-end pipeline

1. Multi-file upload (PDF / images) → `UploadService` + disk + SQLite  
2. Text / OCR → `PdfService`  
3. Structured JSON → `ExtractionService` (LLM)  
4. Visit merge → `TimelineService` / `PatientPipelineService`  
5. Conflicts → `ConflictService` (rule KB)  
6. Lab trends → `LabService` (+ optional LLM narrative)  
7. Follow-up Q&A → `RagPipeline` (chunk · embed · retrieve · generate) + confidence  

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| API | `backend/api` | HTTP routes, deps, request validation |
| Models | `backend/models` | Pydantic schemas + SQLAlchemy metadata |
| Services | `backend/services` | PDF, extraction, timeline, conflicts, labs, pipeline |
| RAG | `backend/rag` | Embeddings, vector store, pipeline |
| Utils | `backend/utils` | Settings, LLM factory |
| UI | `frontend/src` | Pages, components, API client |

## LLM switching

`LLM_PROVIDER=ollama|openai` selects the provider via `backend/utils/llm.py`.  
Hosted demos should use OpenAI; local demos can use Ollama.  
Embeddings default to `BAAI/bge-small-en-v1.5` (hashing fallback if unavailable).

## Deployment targets

- Frontend → Vercel (`frontend/`) — set `VITE_API_BASE_URL` at build time  
- Backend → Render (`backend/Dockerfile`) — set `OPENAI_API_KEY` + `CORS_ORIGINS` / `FRONTEND_URL`
