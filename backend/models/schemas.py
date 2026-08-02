"""Pydantic request/response schemas (stubs — no business logic)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    environment: str
    llm_provider: str


class ConfidenceScore(BaseModel):
    """Confidence metadata attached to every AI answer."""

    score: float = Field(..., ge=0.0, le=1.0, description="Confidence between 0 and 1")
    rationale: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class UploadedFileInfo(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime
    checksum_sha256: Optional[str] = None


class UploadResponse(BaseModel):
    files: List[UploadedFileInfo]
    message: str = "Upload accepted"
    count: int = 0


class UploadListResponse(BaseModel):
    files: List[UploadedFileInfo]
    count: int


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------


class ExtractedPageSchema(BaseModel):
    page_number: int = Field(..., ge=1)
    text: str
    method: str  # text | ocr | empty
    char_count: int = Field(..., ge=0)
    warning: Optional[str] = None


class PdfTextExtractionResponse(BaseModel):
    """JSON payload returned by the PDF text extraction endpoint."""

    file_id: Optional[str] = None
    filename: Optional[str] = None
    source_path: str
    page_count: int
    pages: List[ExtractedPageSchema]
    full_text: str
    ocr_page_numbers: List[int] = Field(default_factory=list)
    text_page_numbers: List[int] = Field(default_factory=list)
    empty_page_numbers: List[int] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Extraction / structured medical data
# ---------------------------------------------------------------------------


class Medicine(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class LabResult(BaseModel):
    test_name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = None  # e.g. normal | high | low


class VitalSign(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None


class MedicalExtraction(BaseModel):
    """Structured medical fields extracted by the LLM."""

    patient_name: Optional[str] = None
    hospital: Optional[str] = None
    doctor: Optional[str] = None
    visit_date: Optional[str] = None
    diagnosis: List[str] = Field(default_factory=list)
    medicines: List[Medicine] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    lab_results: List[LabResult] = Field(default_factory=list)
    vital_signs: List[VitalSign] = Field(default_factory=list)


class StructuredExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw medical report text")


class MedicalExtractionResponse(BaseModel):
    data: MedicalExtraction
    confidence: ConfidenceScore
    llm_provider: str
    source: str = "text"  # text | file
    file_id: Optional[str] = None


class VisitRecord(BaseModel):
    visit_id: str
    visit_date: Optional[datetime] = None
    source_file_id: Optional[str] = None
    medicines: List[Medicine] = Field(default_factory=list)
    lab_results: List[LabResult] = Field(default_factory=list)
    raw_notes: Optional[str] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResponse(BaseModel):
    """Legacy wrapper kept for compatibility; prefer MedicalExtractionResponse."""

    file_id: str
    visit: VisitRecord
    confidence: ConfidenceScore


# ---------------------------------------------------------------------------
# Timeline / analysis
# ---------------------------------------------------------------------------


class PatientTimeline(BaseModel):
    patient_id: Optional[str] = None
    visits: List[VisitRecord] = Field(default_factory=list)


class ConflictFinding(BaseModel):
    type: str  # duplicate | dosage_conflict | allergy_conflict | interaction
    severity: str  # Low | Medium | High
    title: str
    explanation: str
    related_medicines: List[str] = Field(default_factory=list)
    related_allergies: List[str] = Field(default_factory=list)
    confidence: ConfidenceScore
    description: Optional[str] = Field(
        default=None,
        description="Alias of explanation for backwards compatibility",
    )

    def model_post_init(self, __context: Any) -> None:
        if self.description is None:
            self.description = self.explanation


class SeveritySummary(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    total: int = 0


class PrescriptionAnalysisRequest(BaseModel):
    medicines: List[Medicine] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)


class PrescriptionAnalysisResponse(BaseModel):
    findings: List[ConflictFinding] = Field(default_factory=list)
    summary: SeveritySummary
    medicines_analyzed: int = 0
    allergies_considered: int = 0


# ---------------------------------------------------------------------------
# Lab trends
# ---------------------------------------------------------------------------


class LabVisitInput(BaseModel):
    visit_id: Optional[str] = None
    visit_date: str = Field(..., description="Visit date (ISO preferred)")
    labs: List[LabResult] = Field(default_factory=list)


class LabTrendRequest(BaseModel):
    patient_id: Optional[str] = None
    visits: List[LabVisitInput] = Field(default_factory=list)
    include_ai_explanation: bool = True


class LabDataPoint(BaseModel):
    visit_id: Optional[str] = None
    visit_date: str
    value: float
    unit: Optional[str] = None
    status: str = "unknown"  # normal | high | low | unknown
    is_abnormal: bool = False


class LabTrendSeries(BaseModel):
    test_name: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    points: List[LabDataPoint] = Field(default_factory=list)
    direction: str  # rising | falling | stable | insufficient_data
    percent_change: Optional[float] = None
    is_abnormal_trend: bool = False
    severity: str = "None"  # Low | Medium | High | None
    trend_summary: str = ""


class LabChartSeries(BaseModel):
    """Chart-ready series for frontend graph libraries (e.g. Recharts)."""

    test_name: str
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    is_abnormal_trend: bool = False
    severity: str = "None"
    data: List[Dict[str, Any]] = Field(default_factory=list)


class LabTrendResponse(BaseModel):
    patient_id: Optional[str] = None
    visit_count: int = 0
    series: List[LabTrendSeries] = Field(default_factory=list)
    abnormal_trends: List[LabTrendSeries] = Field(default_factory=list)
    charts: List[LabChartSeries] = Field(default_factory=list)
    ai_explanation: Optional[str] = None
    confidence: ConfidenceScore
    llm_provider: Optional[str] = None


class AnalysisResponse(BaseModel):
    timeline: PatientTimeline
    findings: List[ConflictFinding] = Field(default_factory=list)
    lab_trends: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    patient_id: Optional[str] = None
    session_id: Optional[UUID] = None
    top_k: int = Field(default=5, ge=1, le=20)


class RagSource(BaseModel):
    document_id: str
    excerpt: str
    score: Optional[float] = None
    title: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RagQueryResponse(BaseModel):
    answer: str
    confidence: ConfidenceScore
    sources: List[RagSource] = Field(default_factory=list)
    llm_provider: Optional[str] = None
    retrieval_backend: Optional[str] = None


class RagDocumentInput(BaseModel):
    content: str = Field(..., min_length=1)
    document_id: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = "manual"
    patient_id: Optional[str] = None
    visit_date: Optional[str] = None
    file_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RagIngestRequest(BaseModel):
    documents: List[RagDocumentInput] = Field(default_factory=list)
    file_ids: List[str] = Field(
        default_factory=list,
        description="Optional uploaded PDF file IDs to extract and ingest",
    )
    patient_id: Optional[str] = None


class RagIngestResponse(BaseModel):
    documents_ingested: int
    chunks_indexed: int
    backend: str
    embedding_backend: str
    message: str = "Documents ingested"
