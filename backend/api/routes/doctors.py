"""Local doctor recommendation routes."""

from fastapi import APIRouter, Depends

from backend.api.deps import get_app_settings
from backend.models.schemas import DoctorRecommendRequest, DoctorRecommendResponse
from backend.services.doctor_service import DoctorService
from backend.utils.config import Settings

router = APIRouter(prefix="/doctors", tags=["doctors"])


def get_doctor_service(settings: Settings = Depends(get_app_settings)) -> DoctorService:
    return DoctorService(settings)


@router.post("/recommend", response_model=DoctorRecommendResponse)
async def recommend_doctors(
    payload: DoctorRecommendRequest,
    service: DoctorService = Depends(get_doctor_service),
) -> DoctorRecommendResponse:
    """
    Map a flagged issue to a specialty, then search real nearby clinics/doctors.

    Default source: OpenStreetMap (Nominatim + Overpass). Optional Google Places
    if GOOGLE_PLACES_API_KEY is set. Never returns fabricated listings.
    """
    return await service.recommend(payload)
