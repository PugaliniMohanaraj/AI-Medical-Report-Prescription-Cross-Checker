"""RAG ingest and query routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_app_settings
from backend.models.database import get_db
from backend.models.schemas import (
    RagIngestRequest,
    RagIngestResponse,
    RagQueryRequest,
    RagQueryResponse,
)
from backend.rag.pipeline import RagError, RagPipeline
from backend.services.pdf_service import PdfExtractionError, PdfService
from backend.services.upload_service import UploadService
from backend.utils.config import Settings
from backend.utils.paths import get_upload_dir

router = APIRouter(prefix="/rag", tags=["rag"])

_pipeline: RagPipeline | None = None


def get_rag_pipeline(settings: Settings = Depends(get_app_settings)) -> RagPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RagPipeline(settings=settings)
    return _pipeline


def get_pdf_service(settings: Settings = Depends(get_app_settings)) -> PdfService:
    return PdfService(settings)


def get_upload_service(settings: Settings = Depends(get_app_settings)) -> UploadService:
    return UploadService(settings)


@router.post("/ingest", response_model=RagIngestResponse, status_code=status.HTTP_201_CREATED)
async def rag_ingest(
    payload: RagIngestRequest,
    db: AsyncSession = Depends(get_db),
    pipeline: RagPipeline = Depends(get_rag_pipeline),
    pdf_service: PdfService = Depends(get_pdf_service),
    upload_service: UploadService = Depends(get_upload_service),
    settings: Settings = Depends(get_app_settings),
) -> RagIngestResponse:
    """
    Ingest free-text documents and/or uploaded PDF file IDs into the RAG index.
    """
    documents: list[dict] = []

    for doc in payload.documents:
        item = doc.model_dump()
        if payload.patient_id and not item.get("patient_id"):
            item["patient_id"] = payload.patient_id
        documents.append(item)

    for file_id in payload.file_ids:
        info = await upload_service.get_upload(file_id, db)
        if info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload not found: {file_id}",
            )
        pdf_path = get_upload_dir(settings) / f"{file_id}.pdf"
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stored PDF missing for file_id={file_id}",
            )
        try:
            extracted = await pdf_service.extract(pdf_path)
        except PdfExtractionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        if not extracted.full_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No text extracted from file_id={file_id}",
            )
        documents.append(
            {
                "document_id": file_id,
                "content": extracted.full_text,
                "title": info.filename,
                "source": "pdf_upload",
                "file_id": file_id,
                "patient_id": payload.patient_id,
            }
        )

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide documents and/or file_ids to ingest",
        )

    try:
        result = await pipeline.ingest(documents)
    except RagError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return RagIngestResponse(
        documents_ingested=result["documents_ingested"],
        chunks_indexed=result["chunks_indexed"],
        backend=result["backend"],
        embedding_backend=result["embedding_backend"],
        message=f"Indexed {result['chunks_indexed']} chunk(s) from {result['documents_ingested']} document(s).",
    )


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(
    payload: RagQueryRequest,
    pipeline: RagPipeline = Depends(get_rag_pipeline),
) -> RagQueryResponse:
    """
    Answer follow-up questions via RAG with confidence and supporting references.

    Example questions:
    - When was diabetes diagnosed?
    - Did any medicine conflict?
    - What changed between visits?
    """
    try:
        return await pipeline.query(
            payload.question,
            top_k=payload.top_k,
            patient_id=payload.patient_id,
        )
    except RagError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
