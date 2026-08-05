"""Analysis routes: text extraction, AI structuring, timeline, conflicts, labs."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_app_settings
from backend.models.database import get_db
from backend.models.schemas import (
    AnalysisResponse,
    ExtractedPageSchema,
    LabTrendRequest,
    LabTrendResponse,
    MedicalExtractionResponse,
    PatientOverviewResponse,
    PdfTextExtractionResponse,
    PrescriptionAnalysisRequest,
    PrescriptionAnalysisResponse,
    ProcessUploadsRequest,
    ProcessUploadsResponse,
    StructuredExtractRequest,
    VisitRecord,
)
from backend.services.conflict_service import ConflictService
from backend.services.extraction_service import ExtractionError, ExtractionService
from backend.services.lab_service import LabService
from backend.services.patient_pipeline_service import PatientPipelineService
from backend.services.pdf_service import PdfExtractionError, PdfService
from backend.services.timeline_service import TimelineService
from backend.services.upload_service import UploadService
from backend.utils.config import Settings
from backend.utils.llm import get_llm_client

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_pdf_service(settings: Settings = Depends(get_app_settings)) -> PdfService:
    return PdfService(settings)


def get_upload_service(settings: Settings = Depends(get_app_settings)) -> UploadService:
    return UploadService(settings)


def get_extraction_service(settings: Settings = Depends(get_app_settings)) -> ExtractionService:
    return ExtractionService(settings=settings, llm=get_llm_client(settings))


def get_conflict_service() -> ConflictService:
    return ConflictService()


def get_lab_service(settings: Settings = Depends(get_app_settings)) -> LabService:
    # LLM is resolved lazily inside LabService only when AI explanation is requested.
    return LabService(settings=settings)


def get_pipeline_service(settings: Settings = Depends(get_app_settings)) -> PatientPipelineService:
    return PatientPipelineService(settings)


def get_timeline_service() -> TimelineService:
    return TimelineService()


@router.post("/extract-text/{file_id}", response_model=PdfTextExtractionResponse)
async def extract_pdf_text(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    pdf_service: PdfService = Depends(get_pdf_service),
    upload_service: UploadService = Depends(get_upload_service),
) -> PdfTextExtractionResponse:
    """
    Extract text from an uploaded PDF or image.

    Uses selectable text when available; automatically OCRs pages/images with no text.
    Returns a structured JSON payload.
    """
    info = await upload_service.get_upload(file_id, db)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    stored_path = await upload_service.get_stored_path(file_id, db)
    if stored_path is None or not stored_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file is missing on disk",
        )

    try:
        result = await pdf_service.extract(stored_path)
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PdfTextExtractionResponse(
        file_id=file_id,
        filename=info.filename,
        source_path=result.source_path,
        page_count=result.page_count,
        pages=[ExtractedPageSchema(**page.to_dict()) for page in result.pages],
        full_text=result.full_text,
        ocr_page_numbers=result.ocr_page_numbers,
        text_page_numbers=result.text_page_numbers,
        empty_page_numbers=result.empty_page_numbers,
        metadata=result.metadata,
    )


@router.post("/extract-structured", response_model=MedicalExtractionResponse)
async def extract_structured_from_text(
    payload: StructuredExtractRequest,
    extraction_service: ExtractionService = Depends(get_extraction_service),
) -> MedicalExtractionResponse:
    """Extract structured medical JSON from raw text via the configured LLM."""
    try:
        result = await extraction_service.extract(payload.text)
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return result


@router.post("/extract/{file_id}", response_model=MedicalExtractionResponse)
async def extract_structured_from_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    pdf_service: PdfService = Depends(get_pdf_service),
    upload_service: UploadService = Depends(get_upload_service),
    extraction_service: ExtractionService = Depends(get_extraction_service),
) -> MedicalExtractionResponse:
    """
    Extract text from an uploaded PDF or image, then run AI medical information extraction.
    """
    info = await upload_service.get_upload(file_id, db)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    stored_path = await upload_service.get_stored_path(file_id, db)
    if stored_path is None or not stored_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file is missing on disk",
        )

    try:
        pdf_result = await pdf_service.extract(stored_path)
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not pdf_result.full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the file",
        )

    try:
        result = await extraction_service.extract(pdf_result.full_text)
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    result.source = "file"
    result.file_id = file_id
    return result


@router.post("/prescription", response_model=PrescriptionAnalysisResponse)
async def analyze_prescription(
    payload: PrescriptionAnalysisRequest,
    conflict_service: ConflictService = Depends(get_conflict_service),
) -> PrescriptionAnalysisResponse:
    """
    Analyze a prescription for duplicates, dosage conflicts, allergy conflicts,
    and possible drug interactions. Every finding includes severity and explanation.
    """
    if not payload.medicines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one medicine is required for prescription analysis",
        )
    return await conflict_service.analyze(payload.medicines, payload.allergies)


@router.post("/process", response_model=ProcessUploadsResponse)
async def process_uploads(
    payload: ProcessUploadsRequest | None = None,
    db: AsyncSession = Depends(get_db),
    pipeline: PatientPipelineService = Depends(get_pipeline_service),
) -> ProcessUploadsResponse:
    """
    Run the AI pipeline on uploaded documents:
    extract text → structured medical extraction → store visits → RAG ingest.
    """
    body = payload or ProcessUploadsRequest()
    try:
        return await pipeline.process_uploads(
            db,
            file_ids=body.file_ids or None,
            patient_id=body.patient_id,
            ingest_rag=body.ingest_rag,
        )
    except Exception as exc:  # noqa: BLE001
        # Surface a JSON error (with CORS) instead of a dropped connection.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc


@router.get("/patient", response_model=PatientOverviewResponse)
async def get_patient_overview(
    patient_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    pipeline: PatientPipelineService = Depends(get_pipeline_service),
) -> PatientOverviewResponse:
    """Return merged patient timeline, medicines, labs, and safety findings from uploads."""
    return await pipeline.get_overview(db, patient_id=patient_id, include_analysis=True)


@router.get("/timeline", response_model=PatientOverviewResponse)
async def get_timeline(
    patient_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    pipeline: PatientPipelineService = Depends(get_pipeline_service),
) -> PatientOverviewResponse:
    """Chronological visits extracted from uploaded reports."""
    return await pipeline.get_overview(db, patient_id=patient_id, include_analysis=False)


@router.post("/timeline", response_model=AnalysisResponse)
async def build_timeline(
    patient_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    pipeline: PatientPipelineService = Depends(get_pipeline_service),
    timeline_service: TimelineService = Depends(get_timeline_service),
    conflict_service: ConflictService = Depends(get_conflict_service),
) -> AnalysisResponse:
    """Merge stored visits into a timeline and run prescription conflict checks."""
    overview = await pipeline.get_overview(db, patient_id=patient_id, include_analysis=False)
    visit_records = [
        VisitRecord(
            visit_id=visit.id,
            source_file_id=visit.source_file_id,
            medicines=visit.medicines,
            lab_results=visit.labs,
            raw_notes=visit.summary,
            structured_data={
                "diagnosis": visit.diagnosis,
                "allergies": visit.allergies,
                "hospital": visit.hospital,
                "doctor": visit.doctor,
                "date": visit.date,
            },
        )
        for visit in overview.visits
    ]
    timeline = await timeline_service.merge_visits(
        visit_records,
        patient_id=overview.patient_id,
    )
    findings = []
    if overview.medicines:
        rx = await conflict_service.analyze(overview.medicines, overview.allergies)
        findings = rx.findings
    return AnalysisResponse(
        timeline=timeline,
        findings=findings,
        lab_trends={},
    )


@router.post("/labs", response_model=LabTrendResponse)
async def analyze_lab_trends(
    payload: LabTrendRequest,
    lab_service: LabService = Depends(get_lab_service),
) -> LabTrendResponse:
    """
    Compare lab values across visits, build chart-ready series, highlight abnormal
    trends, and produce an AI explanation.
    """
    if not payload.visits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one visit with lab results is required",
        )
    has_labs = any(visit.labs for visit in payload.visits)
    if not has_labs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No lab results found in the provided visits",
        )
    return await lab_service.analyze(payload)


@router.get("/labs/{patient_id}", response_model=LabTrendResponse)
async def lab_trends_by_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    pipeline: PatientPipelineService = Depends(get_pipeline_service),
) -> LabTrendResponse:
    """Patient-scoped lab trend lookup from stored extractions."""
    overview = await pipeline.get_overview(db, patient_id=patient_id, include_analysis=True)
    if overview.lab_trends is not None:
        return overview.lab_trends
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No lab results found for patient_id={patient_id}",
    )
