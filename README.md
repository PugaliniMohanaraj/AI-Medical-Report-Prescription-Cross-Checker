# MedCross — AI Medical Report & Prescription Cross-Checker

End-to-end clinical document intelligence for the **YGC AI Competition 2026 (Round 1)**:
upload multi-visit medical PDFs/images, extract structured data with AI, merge a patient
timeline, flag prescription conflicts, track lab trends, and ask grounded follow-up questions
with confidence scores.

> **Not a medical device.** The app supports clinical review only and must never be treated as a diagnosis.

## What it does

1. **Upload** multiple lab reports, prescriptions, and discharge summaries  
2. **AI extraction** of medicines, dosages, labs, dates, allergies, and diagnoses  
3. **Timeline** merge across visits and providers  
4. **Safety cross-check** — duplicates, dosage conflicts, interactions, allergy risks  
5. **Lab trends** with plain-language explanations  
6. **RAG chat** across all ingested documents, with citations + confidence  

## Tech stack

| Area | Stack |
|------|--------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, React Router, Axios, Recharts |
| Backend | FastAPI, Uvicorn, Pydantic, SQLAlchemy + SQLite, PyMuPDF, RapidOCR |
| AI | Ollama (local) **or** OpenAI — switch via `LLM_PROVIDER` |
| RAG | LangChain chunking · `BAAI/bge-small-en-v1.5` · ChromaDB (memory fallback) |
| Deploy | Frontend → Vercel · Backend → Render (Docker) |

## Repository layout

```
├── frontend/                 # React SPA
├── backend/
│   ├── api/                  # Routes
│   ├── models/               # Schemas + SQLAlchemy
│   ├── services/             # PDF, extraction, conflicts, labs, pipeline
│   ├── rag/                  # Embeddings, vector store, Q&A pipeline
│   ├── utils/                # Settings & LLM factory
│   └── main.py
├── docs/
├── docker-compose.yml
└── README.md
```

See [docs/architecture.md](docs/architecture.md) for layering details.

## Prerequisites

- Node.js 20+
- Python 3.11+ (prefer 3.11–3.12 on Windows)
- (Optional local) [Ollama](https://ollama.com) with `llama3.1` pulled
- (Optional) Docker / Docker Compose
- **Hosted demo:** OpenAI API key (Ollama is not available on Render free tier)

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

# Full AI / RAG stack (recommended for demos)
# pip install -r backend/requirements-ai.txt

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
| `OPENAI_API_KEY` | **Required** when provider is openai | — |
| `OPENAI_MODEL` | OpenAI chat model | `gpt-4o-mini` |
| `CORS_ORIGINS` | Comma-separated allowed origins (no trailing slash) | Vite localhost |
| `FRONTEND_URL` | Optional; merged into CORS (set to Vercel URL) | — |
| `EMBEDDING_MODEL` | Sentence-transformers model | `BAAI/bge-small-en-v1.5` |
| `UPLOAD_DIR` | Upload directory | `backend/uploads` |
| `CHROMA_PERSIST_DIR` | Chroma persistence path | `backend/data/chroma` |
| `SQLITE_DB_PATH` | SQLite metadata path | `backend/data/metadata.db` |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API base, e.g. `http://localhost:8000/api/v1` |

**Production:** set `VITE_API_BASE_URL` to `https://<your-render-service>.onrender.com/api/v1` in Vercel **before** building. Vite bakes this at build time.

## Switching LLM providers

```env
# Local
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1

# Cloud / Render
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Factory: `backend/utils/llm.py`.

## Tests

```bash
# from repo root, venv active
pip install -r backend/requirements.txt
pytest
```

## Deployment (checklist)

### Backend → Render

1. Deploy with `backend/Dockerfile` (or `render.yaml` blueprint)
2. Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY`
3. Set `CORS_ORIGINS` **or** `FRONTEND_URL` to your exact Vercel origin  
   (example: `https://medcross.vercel.app` — no trailing slash)
4. Smoke-test `/api/v1/health`

### Frontend → Vercel

1. Root directory: `frontend`
2. Build: `npm run build` · Output: `dist`
3. Set `VITE_API_BASE_URL=https://<render>/api/v1`
4. Redeploy after changing the env var

`frontend/vercel.json` handles SPA rewrites.

### Pre-demo tip

Render free instances sleep. Wake the API and run one upload→process cycle **before** judges join. Uploads/SQLite may reset on free-tier restarts — re-upload the sample set if needed.

## License

Prepared for AI competition use. Add a license before public release if required.
