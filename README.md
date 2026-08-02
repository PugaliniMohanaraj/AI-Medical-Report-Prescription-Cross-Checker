# Medical Report & Prescription Cross-Checker

Production-ready **project scaffold** for an AI competition: multi-PDF medical report analysis, prescription conflict detection, lab trends, and RAG follow-up Q&A with confidence scores.

> **Scope of this commit:** architecture, configuration, and stubs only. Business logic is intentionally not implemented yet.

## Tech stack

| Area | Stack |
|------|--------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, React Router, Axios, Recharts |
| Backend | FastAPI, Pydantic, LangChain, ChromaDB, PyMuPDF, Uvicorn |
| AI | Llama 3.1 (Ollama) **or** OpenAI — switch via `LLM_PROVIDER` |
| Embeddings | `BAAI/bge-small-en-v1.5` |
| Data | SQLite (metadata) · ChromaDB (vectors) |
| Deploy | Frontend → Vercel · Backend → Render |

## Repository layout

```
├── frontend/                 # React SPA
│   ├── src/api/              # Axios client & endpoint helpers
│   ├── src/components/
│   ├── src/pages/
│   ├── src/hooks/
│   ├── src/types/
│   └── src/utils/
├── backend/
│   ├── api/                  # Routes & dependencies
│   ├── models/               # Pydantic schemas + SQLAlchemy
│   ├── services/             # Domain service stubs
│   ├── rag/                  # Embeddings, vector store, pipeline stubs
│   ├── utils/                # Settings & LLM factory
│   ├── uploads/              # PDF storage
│   ├── tests/
│   └── main.py               # FastAPI entrypoint
├── docs/                     # Architecture & API notes
├── docker-compose.yml
└── README.md
```

See [docs/architecture.md](docs/architecture.md) for layering details.

## Prerequisites

- Node.js 20+
- Python 3.11+ (3.10 also works; 3.13 may lack some AI package wheels on Windows)
- (Optional) [Ollama](https://ollama.com) with `llama3.1` pulled
- (Optional) Docker / Docker Compose

## Quick start

### 1. Backend

```bash
# from repo root
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r backend/requirements.txt
copy backend\.env.example backend\.env   # Windows
# cp backend/.env.example backend/.env   # macOS / Linux

# Optional AI / RAG dependencies (LangChain, ChromaDB, embeddings)
# Prefer Python 3.11–3.12. On Windows you may need Visual C++ Build Tools.
# pip install -r backend/requirements-ai.txt

# Run from repo root so `backend` is importable
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/api/v1/health

### 2. Frontend

```bash
cd frontend
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
npm install
npm run dev
```

App: http://localhost:5173

### 3. Docker Compose

```bash
copy backend\.env.example backend\.env
docker compose up --build
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:3000

## Environment variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `ollama` or `openai` | `ollama` |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name | `llama3.1` |
| `OPENAI_API_KEY` | Required when provider is openai | — |
| `OPENAI_MODEL` | OpenAI chat model | `gpt-4o-mini` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `BAAI/bge-small-en-v1.5` |
| `CORS_ORIGINS` | Comma-separated allowed origins | Vite localhost |
| `UPLOAD_DIR` | PDF upload directory | `uploads` |
| `CHROMA_PERSIST_DIR` | Chroma persistence path | `data/chroma` |
| `SQLITE_DB_PATH` | SQLite metadata path | `data/metadata.db` |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API base, e.g. `http://localhost:8000/api/v1` |

## Switching LLM providers

```env
# Local Llama 3.1
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1

# Or OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Factory: `backend/utils/llm.py` (wiring stubbed until the AI phase).

## Tests

```bash
# from repo root, venv active
pip install -r backend/requirements.txt
pytest
```

## AI dependencies

Core API deps live in `backend/requirements.txt`.  
Full RAG stack: `backend/requirements-ai.txt` (used by Docker / Render).

```bash
pip install -r backend/requirements-ai.txt
```

## Deployment

### Frontend → Vercel

- Root directory: `frontend`
- Build: `npm run build`
- Output: `dist`
- Set `VITE_API_BASE_URL` to your Render API URL (`…/api/v1`)

`frontend/vercel.json` is included for SPA rewrites.

### Backend → Render

- Use `backend/Dockerfile` **or** native Python with:
  - Build: `pip install -r backend/requirements.txt`
  - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Set env vars from `backend/.env.example`
- Persist `uploads` / `data` via a disk if available

`render.yaml` blueprint is included as a starting point.

## Planned features (next phases)

1. ~~Multi-PDF upload & storage~~
2. ~~PyMuPDF text extraction (+ OCR fallback)~~
3. ~~AI structured medical extraction (OpenAI / local Llama)~~
4. Patient timeline merge  
5. ~~Duplicate / dosage / allergy / interaction detection~~
6. ~~Lab trend analytics (+ graphs / AI explanations)~~
7. ~~RAG pipeline + confidence scores~~
8. Interactive Recharts dashboard  

### OCR note

Scanned/image-only pages use PyMuPDF's Tesseract integration (`page.get_textpage_ocr`).
Install [Tesseract](https://github.com/tesseract-ocr/tesseract) language data and, if needed,
set `TESSDATA_PATH` in `backend/.env`.

### RAG note

Core install includes LangChain text splitters. For production ChromaDB + BGE embeddings:

```bash
pip install -r backend/requirements-ai.txt
```

Set `RAG_VECTOR_BACKEND=auto|chroma|memory`. LLM answers use `LLM_PROVIDER=ollama|openai`.

## License

Prepared for AI competition use. Add a license before public release if required.
