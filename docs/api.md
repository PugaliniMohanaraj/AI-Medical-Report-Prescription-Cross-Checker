# API Reference

Base URL (local): `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs`

## Health

### `GET /health`

Returns service status and configured LLM provider.

**Response `200`**

```json
{
  "status": "ok",
  "app_name": "Medical Report Cross-Checker",
  "environment": "development",
  "llm_provider": "ollama"
}
```

## Uploads

### `POST /uploads`

Multipart form field: `files` (one or more PDF or image files).

**Validation**
- Allowed: `.pdf`, common image types (png/jpg/webp/tiff/bmp/gif)
- Max files / size from settings (`MAX_FILES_PER_REQUEST`, `MAX_UPLOAD_SIZE_MB`)

**Response `201`**

```json
{
  "files": [
    {
      "file_id": "uuid",
      "filename": "report.pdf",
      "size_bytes": 12345,
      "content_type": "application/pdf",
      "uploaded_at": "2026-01-01T00:00:00Z",
      "checksum_sha256": "..."
    }
  ],
  "count": 1,
  "message": "Successfully uploaded 1 file(s)."
}
```

### `GET /uploads`

List stored upload metadata.

### `GET /uploads/{file_id}`

Fetch one file's metadata.

### `DELETE /uploads/{file_id}`

Remove file from disk and metadata (`204`).

## Analysis

### `POST /analysis/extract-text/{file_id}`

Extract text from an uploaded PDF/image with PyMuPDF (+ OCR when needed).

### `POST /analysis/extract-structured`

LLM structured extraction from raw text.

### `POST /analysis/extract/{file_id}`

Extract text then structure in one call.

### `POST /analysis/prescription`

Rule-based prescription conflict analysis (duplicates, dosage, interactions, allergies).

### `POST /analysis/process`

End-to-end: extract pending uploads (or selected `file_ids`), persist visit records,
optionally ingest into RAG. Primary demo path after upload.

### `GET /analysis/patient`

Merged patient overview: timeline, medicines, labs, safety findings, disclaimer.

### `GET /analysis/timeline` · `POST /analysis/timeline`

Chronological visit merge; POST also runs conflict checks.

### `POST /analysis/labs`

Compare lab values across visits, return chart-ready series, highlight abnormal
trends, and produce an AI explanation.

**Body**

```json
{
  "patient_id": "demo",
  "include_ai_explanation": true,
  "visits": [
    {
      "visit_id": "v1",
      "visit_date": "2024-01-10",
      "labs": [{ "test_name": "HbA1c", "value": "6.8", "unit": "%" }]
    },
    {
      "visit_id": "v2",
      "visit_date": "2024-08-10",
      "labs": [{ "test_name": "HbA1c", "value": "7.9", "unit": "%" }]
    }
  ]
}
```

**Response** includes `series`, `abnormal_trends`, `charts` (Recharts-ready), `ai_explanation`, and `confidence`.

### `GET /analysis/labs/{patient_id}`

Lab trends for a patient derived from stored extracted visits (via pipeline overview).

## RAG

### `POST /rag/ingest`

Index free-text documents and/or uploaded PDF `file_ids`.

```json
{
  "patient_id": "p1",
  "documents": [
    { "document_id": "visit-1", "title": "Visit note", "content": "..." }
  ],
  "file_ids": ["uuid-of-uploaded-pdf"]
}
```

### `POST /rag/query`

Answer follow-up questions with confidence + supporting references.

Example questions:
- When was diabetes diagnosed?
- Did any medicine conflict?
- What changed between visits?

```json
{
  "question": "When was diabetes diagnosed?",
  "patient_id": "p1",
  "top_k": 5
}
```

**Response `200`**

```json
{
  "answer": "Diabetes was diagnosed on 2023-02-10...",
  "confidence": { "score": 0.84, "rationale": "..." },
  "sources": [
    {
      "document_id": "visit-1",
      "title": "Visit 2023-02-10",
      "excerpt": "Patient Jane Doe diagnosed with Type 2 Diabetes...",
      "score": 0.81
    }
  ],
  "llm_provider": "ollama",
  "retrieval_backend": "chroma"
}
```
