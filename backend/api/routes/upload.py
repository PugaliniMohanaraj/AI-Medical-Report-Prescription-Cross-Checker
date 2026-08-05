"""Upload routes for PDFs and images."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_app_settings
from backend.models.database import get_db
from backend.models.schemas import UploadListResponse, UploadedFileInfo, UploadResponse
from backend.services.upload_service import UploadService, UploadValidationError
from backend.utils.config import Settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


def get_upload_service(settings: Settings = Depends(get_app_settings)) -> UploadService:
    return UploadService(settings)


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: list[UploadFile] = File(
        ...,
        description="One or more PDF or image files (png, jpg, jpeg, webp, tiff, bmp, gif)",
    ),
    db: AsyncSession = Depends(get_db),
    service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    """Accept and store one or more PDF or image uploads."""
    try:
        saved = await service.save_uploads(files, db)
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Upload validation failed", "errors": exc.errors},
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded files on disk.",
        ) from exc

    return UploadResponse(
        files=saved,
        count=len(saved),
        message=f"Successfully uploaded {len(saved)} file(s).",
    )


@router.get("", response_model=UploadListResponse)
async def list_uploads(
    db: AsyncSession = Depends(get_db),
    service: UploadService = Depends(get_upload_service),
) -> UploadListResponse:
    """List previously uploaded file metadata."""
    files = await service.list_uploads(db)
    return UploadListResponse(files=files, count=len(files))


@router.get("/{file_id}", response_model=UploadedFileInfo)
async def get_upload(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    service: UploadService = Depends(get_upload_service),
) -> UploadedFileInfo:
    """Fetch metadata for a single uploaded file."""
    info = await service.get_upload(file_id, db)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return info


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    service: UploadService = Depends(get_upload_service),
) -> None:
    """Delete an uploaded file and its metadata."""
    deleted = await service.delete_upload(file_id, db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
