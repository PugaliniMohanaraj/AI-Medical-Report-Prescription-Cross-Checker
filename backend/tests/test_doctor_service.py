"""Doctor specialty matching tests (no live map calls)."""

from backend.models.schemas import FlagInput
from backend.services.doctor_service import match_specialty


def test_interaction_maps_to_pharmacist() -> None:
    specialty, reason = match_specialty(
        [FlagInput(type="interaction", severity="High", title="Warfarin + Aspirin")]
    )
    assert specialty == "pharmacist"
    assert "interaction" in reason.lower() or "drug" in reason.lower()


def test_allergy_maps_to_allergist() -> None:
    specialty, _reason = match_specialty(
        [FlagInput(type="allergy_conflict", severity="High", title="Penicillin allergy")]
    )
    assert specialty == "allergist"


def test_cardiac_labs_map_to_cardiologist() -> None:
    specialty, _reason = match_specialty(
        [],
        diagnosis=["Hypertension"],
        abnormal_labs=["LDL"],
    )
    assert specialty == "cardiologist"


def test_diabetes_maps_to_endocrinologist() -> None:
    specialty, _reason = match_specialty(
        [FlagInput(title="Rising HbA1c", severity="Medium")],
        primary_diagnosis="Type 2 Diabetes Mellitus",
    )
    assert specialty == "endocrinologist"


def test_high_risk_fallback_is_gp() -> None:
    specialty, _reason = match_specialty(
        [FlagInput(type="other", severity="High", title="Unspecified concern")]
    )
    assert specialty == "general practitioner"
