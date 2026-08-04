"""Patient timeline merge service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.models.schemas import PatientTimeline, VisitRecord


class TimelineService:
    """Merge multiple visit records into a chronological patient timeline."""

    async def merge_visits(
        self,
        visits: list[dict[str, Any]] | list[VisitRecord],
        *,
        patient_id: str | None = None,
    ) -> PatientTimeline:
        normalized: list[VisitRecord] = []
        for item in visits:
            if isinstance(item, VisitRecord):
                normalized.append(item)
            else:
                normalized.append(VisitRecord.model_validate(item))

        def sort_key(visit: VisitRecord) -> tuple[int, str]:
            if visit.visit_date is None:
                return (1, visit.visit_id)
            if isinstance(visit.visit_date, datetime):
                return (0, visit.visit_date.isoformat())
            return (0, str(visit.visit_date))

        ordered = sorted(normalized, key=sort_key)
        return PatientTimeline(patient_id=patient_id, visits=ordered)
