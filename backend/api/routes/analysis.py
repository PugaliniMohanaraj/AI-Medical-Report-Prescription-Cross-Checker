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
    PdfTextExtractionResponse,
    PrescriptionAnalysisRequest,
    PrescriptionAnalysisResponse,
    StructuredExtractRequest,
)
from backend.services.conflict_service import ConflictService
from backend.services.extraction_service import ExtractionError, ExtractionService
from backend.services.lab_service import LabService
from backend.services.pdf_service import PdfExtractionError, PdfService
from backend.services.upload_service import UploadService
from backend.utils.config import Settings
from backend.utils.llm import get_llm_client
from backend.utils.paths import get_upload_dir

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


@router.post("/extract-text/{file_id}", response_model=PdfTextExtractionResponse)
async def extract_pdf_text(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    pdf_service: PdfService = Depends(get_pdf_service),
    upload_service: UploadService = Depends(get_upload_service),
    settings: Settings = Depends(get_app_settings),
) -> PdfTextExtractionResponse:
    """
    Extract text from an uploaded PDF.

    Uses selectable text when available; automatically OCRs pages with no text.
    Returns a structured JSON payload.
    """
    info = await upload_service.get_upload(file_id, db)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    pdf_path = get_upload_dir(settings) / f"{file_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored PDF file is missing on disk",
        )

    try:
        result = await pdf_service.extract(pdf_path)
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
    settings: Settings = Depends(get_app_settings),
) -> MedicalExtractionResponse:
    """
    Extract text from an uploaded PDF, then run AI medical information extraction.
    """
    info = await upload_service.get_upload(file_id, db)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    pdf_path = get_upload_dir(settings) / f"{file_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored PDF file is missing on disk",
        )

    try:
        pdf_result = await pdf_service.extract(pdf_path)
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not pdf_result.full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the PDF",
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


@router.post("/timeline", response_model=AnalysisResponse)
async def build_timeline() -> AnalysisResponse:
    """Merge visits into a patient timeline and run conflict checks. Not implemented yet."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Timeline / conflict analysis is not implemented yet",
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
async def lab_trends_by_patient(patient_id: str) -> LabTrendResponse:
    """
    Patient-scoped lab trend lookup.

    Persistent multi-visit patient storage is not implemented yet — submit visit
    labs via POST /analysis/labs.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"Stored lab history for patient_id={patient_id} is not available yet. "
            "Use POST /analysis/labs with visit lab payloads."
        ),
    )
