# API Reference (Scaffold)

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

Multipart form field: `files` (one or more PDFs).

**Validation**
- `.pdf` extension
- PDF magic bytes (`%PDF`)
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

Extract text from an uploaded PDF with PyMuPDF.

- Uses selectable text when present
- Automatically OCRs pages with no selectable text (requires Tesseract language data)
- Returns structured JSON

**Response `200`**

```json
{
  "file_id": "uuid",
  "filename": "report.pdf",
  "source_path": "...",
  "page_count": 2,
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "method": "text",
      "char_count": 120,
      "warning": null
    }
  ],
  "full_text": "...",
  "ocr_page_numbers": [],
  "text_page_numbers": [1],
  "empty_page_numbers": [],
  "metadata": {}
}
```

### `POST /analysis/extract-structured`

AI medical information extraction from raw text.

**Body**

```json
{ "text": "Patient Name: Jane Doe ..." }
```

**Response `200`**

```json
{
  "data": {
    "patient_name": "Jane Doe",
    "hospital": "City General Hospital",
    "doctor": "Dr. Smith",
    "visit_date": "2024-03-15",
    "diagnosis": ["Type 2 Diabetes Mellitus"],
    "medicines": [
      { "name": "Metformin", "dosage": "500mg", "frequency": "twice daily", "duration": "30 days" }
    ],
    "allergies": ["Penicillin"],
    "lab_results": [{ "test_name": "HbA1c", "value": "7.1", "unit": "%", "reference_range": null, "status": null }],
    "vital_signs": [{ "name": "Blood Pressure", "value": "130/85", "unit": "mmHg" }]
  },
  "confidence": { "score": 0.82, "rationale": "..." },
  "llm_provider": "ollama",
  "source": "text",
  "file_id": null
}
```

Provider switch: `LLM_PROVIDER=ollama|openai`.

### `POST /analysis/extract/{file_id}`

Extract PDF text, then run the same AI medical structuring pipeline (`source: "file"`).

### `POST /analysis/prescription`

Analyze medicines + allergies for:

- duplicate medicines
- dosage conflicts
- allergy conflicts
- possible interactions

Each finding includes severity (`Low` | `Medium` | `High`) and a full explanation.

**Body**

```json
{
  "medicines": [
    { "name": "Warfarin", "dosage": "5mg", "frequency": "daily" },
    { "name": "Aspirin", "dosage": "81mg" },
    { "name": "Amoxicillin", "dosage": "500mg" }
  ],
  "allergies": ["Penicillin"]
}
```

**Response `200`**

```json
{
  "findings": [
    {
      "type": "interaction",
      "severity": "High",
      "title": "Possible interaction: Warfarin + Aspirin",
      "explanation": "Combining warfarin with aspirin increases bleeding risk...",
      "related_medicines": ["Warfarin", "Aspirin"],
      "related_allergies": [],
      "confidence": { "score": 0.85, "rationale": "..." }
    }
  ],
  "summary": { "low": 0, "medium": 0, "high": 2, "total": 2 },
  "medicines_analyzed": 3,
  "allergies_considered": 1
}
```

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

Reserved for persisted patient history (not implemented yet). Use `POST /analysis/labs`.

### `POST /analysis/timeline`

Merge visits and run conflict detection.

**Current status:** `501 Not Implemented`

### `GET /analysis/labs/{patient_id}`

Lab result trends over time.

**Current status:** `501 Not Implemented`

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
