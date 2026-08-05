"""End-to-end upload → extract → persist → analyze pipeline."""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entities import UploadedFileRecord, VisitExtractionRecord
from backend.models.schemas import (
    ConfidenceScore,
    LabResult,
    LabTrendRequest,
    LabVisitInput,
    Medicine,
    MedicalExtraction,
    PatientOverviewResponse,
    ProcessFileResult,
    ProcessUploadsResponse,
    TimelineVisitView,
)
from backend.rag.pipeline import RagError, RagPipeline
from backend.services.conflict_service import ConflictService
from backend.services.extraction_service import ExtractionError, ExtractionService
from backend.services.lab_service import LabService
from backend.services.pdf_service import PdfExtractionError, PdfService
from backend.utils.config import Settings, get_settings
from backend.utils.llm import get_llm_client
from backend.utils.paths import get_upload_dir

logger = logging.getLogger(__name__)

DEFAULT_PATIENT_ID = "default-patient"
DISCLAIMER = (
    "This tool supports clinical review only. It is not a diagnosis. "
    "Consult a doctor or pharmacist for high-risk or low-confidence findings."
)


def _slug_patient_id(name: str | None) -> str:
    if not name or not name.strip():
        return DEFAULT_PATIENT_ID
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:80] or DEFAULT_PATIENT_ID


class PatientPipelineService:
    """Process uploaded documents into structured visits and patient overview."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.upload_dir = get_upload_dir(self.settings)
        self.pdf_service = PdfService(self.settings)
        # Lazy: overview/timeline must work even if OPENAI_API_KEY is missing.
        self._extraction_service: ExtractionService | None = None
        self.conflict_service = ConflictService()
        self.lab_service = LabService(settings=self.settings)
        self._rag: RagPipeline | None = None

    @property
    def extraction_service(self) -> ExtractionService:
        if self._extraction_service is None:
            self._extraction_service = ExtractionService(
                settings=self.settings,
                llm=get_llm_client(self.settings),
            )
        return self._extraction_service

    def _rag_pipeline(self) -> RagPipeline:
        if self._rag is None:
            self._rag = RagPipeline(settings=self.settings)
        return self._rag

    async def process_uploads(
        self,
        db: AsyncSession,
        *,
        file_ids: list[str] | None = None,
        patient_id: str | None = None,
        ingest_rag: bool = True,
    ) -> ProcessUploadsResponse:
        uploads = await self._resolve_uploads(db, file_ids)
        if not uploads:
            return ProcessUploadsResponse(
                patient_id=patient_id or DEFAULT_PATIENT_ID,
                message="No uploads found to process.",
                disclaimer=DISCLAIMER,
            )

        results: list[ProcessFileResult] = []
        resolved_patient_id = patient_id
        rag_docs: list[dict[str, Any]] = []

        for upload in uploads:
            existing_result = await db.execute(
                select(VisitExtractionRecord).where(
                    VisitExtractionRecord.source_file_id == upload.id
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is not None:
                if existing.status == "completed":
                    results.append(
                        ProcessFileResult(
                            file_id=upload.id,
                            filename=upload.original_filename,
                            status="skipped",
                            visit_id=existing.id,
                            visit_date=existing.visit_date,
                            patient_name=existing.patient_name,
                            error="Already processed",
                        )
                    )
                    continue
                # Allow retry of previous failures.
                await db.delete(existing)
                await db.flush()

            result = await self._process_one(db, upload, resolved_patient_id)
            results.append(result)
            if result.status == "completed" and result.patient_name and not patient_id:
                # Lock patient id from first successful extraction when not provided.
                if resolved_patient_id in (None, DEFAULT_PATIENT_ID):
                    resolved_patient_id = _slug_patient_id(result.patient_name)

            if result.status == "completed":
                row = await db.get(VisitExtractionRecord, result.visit_id)
                if row and row.full_text.strip():
                    rag_docs.append(
                        {
                            "document_id": row.id,
                            "content": row.full_text,
                            "title": row.source_filename or upload.original_filename,
                            "source": "upload",
                            "file_id": upload.id,
                            "patient_id": row.patient_id,
                            "visit_date": row.visit_date,
                        }
                    )

        await db.commit()

        if not resolved_patient_id:
            # Prefer most common patient_id from new rows.
            resolved_patient_id = await self._latest_patient_id(db) or DEFAULT_PATIENT_ID

        # Re-assign patient_id on newly created rows if we resolved a better id.
        if patient_id is None and resolved_patient_id != DEFAULT_PATIENT_ID:
            for item in results:
                if item.status == "completed" and item.visit_id:
                    row = await db.get(VisitExtractionRecord, item.visit_id)
                    if row and row.patient_id == DEFAULT_PATIENT_ID:
                        row.patient_id = resolved_patient_id
            await db.commit()

        rag_chunks = 0
        if rag_docs and (
            ingest_rag
            or self.settings.app_env == "production"
            or self.settings.embedding_backend == "hash"
        ):
            for doc in rag_docs:
                doc["patient_id"] = resolved_patient_id
            try:
                # Hash + memory on hosted free tier — loading sentence-transformers/torch
                # often OOMs and the browser shows a misleading "Network Error".
                light = (
                    self.settings.app_env == "production"
                    or self.settings.embedding_backend == "hash"
                    or self.settings.rag_vector_backend == "memory"
                )
                rag = RagPipeline(self.settings, force_memory=light)
                self._rag = rag
                ingested = await rag.ingest(rag_docs)
                rag_chunks = int(ingested.get("chunks_indexed") or 0)
            except Exception as exc:  # noqa: BLE001
                logger.warning("RAG ingest after processing failed: %s", exc)

        completed = sum(1 for r in results if r.status == "completed")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")

        return ProcessUploadsResponse(
            patient_id=resolved_patient_id,
            processed=completed,
            failed=failed,
            skipped=skipped,
            results=results,
            rag_chunks_indexed=rag_chunks,
            message=(
                f"Processed {completed} document(s)"
                + (f", {failed} failed" if failed else "")
                + (f", {skipped} skipped" if skipped else "")
                + "."
            ),
            disclaimer=DISCLAIMER,
        )

    async def get_overview(
        self,
        db: AsyncSession,
        patient_id: str | None = None,
        *,
        include_analysis: bool = True,
    ) -> PatientOverviewResponse:
        upload_count = len((await db.execute(select(UploadedFileRecord))).scalars().all())

        pid = patient_id
        if not pid:
            pid = await self._latest_patient_id(db) or DEFAULT_PATIENT_ID

        rows = (
            await db.execute(
                select(VisitExtractionRecord)
                .where(VisitExtractionRecord.patient_id == pid)
                .where(VisitExtractionRecord.status == "completed")
            )
        ).scalars().all()

        if not rows and patient_id is None:
            # Fall back to any completed extractions.
            rows = (
                await db.execute(
                    select(VisitExtractionRecord).where(
                        VisitExtractionRecord.status == "completed"
                    )
                )
            ).scalars().all()
            if rows:
                pid = rows[0].patient_id

        visits = [self._to_visit_view(row) for row in rows]
        visits.sort(key=lambda v: v.date or "")

        allergies: list[str] = []
        medicines: list[Medicine] = []
        lab_visits: list[LabVisitInput] = []
        diagnoses: list[str] = []
        patient_name = None
        hospital = None
        doctor = None

        for visit in visits:
            patient_name = patient_name or None
            for allergy in visit.allergies:
                if allergy and allergy not in allergies:
                    allergies.append(allergy)
            for med in visit.medicines:
                if med.name:
                    medicines.append(med)
            if visit.labs:
                lab_visits.append(
                    LabVisitInput(
                        visit_id=visit.id,
                        visit_date=visit.date,
                        labs=visit.labs,
                    )
                )
            for dx in visit.diagnosis:
                if dx and dx not in diagnoses:
                    diagnoses.append(dx)

        # Prefer latest non-empty identity fields
        for visit in reversed(visits):
            row = next((r for r in rows if r.id == visit.id), None)
            if row:
                patient_name = patient_name or row.patient_name
                hospital = hospital or row.hospital
                doctor = doctor or row.doctor

        findings = []
        lab_trends = None
        if include_analysis and visits:
            if medicines:
                rx = await self.conflict_service.analyze(medicines, allergies)
                findings = rx.findings
            if lab_visits:
                lab_trends = await self.lab_service.analyze(
                    LabTrendRequest(
                        patient_id=pid,
                        visits=lab_visits,
                        include_ai_explanation=True,
                    )
                )

        return PatientOverviewResponse(
            patient_id=pid,
            patient_name=patient_name,
            hospital=hospital,
            doctor=doctor,
            allergies=allergies,
            primary_diagnosis=", ".join(diagnoses) if diagnoses else None,
            visit_count=len(visits),
            visits=visits,
            medicines=self._dedupe_medicines(medicines),
            lab_visits=lab_visits,
            findings=findings,
            lab_trends=lab_trends,
            has_uploads=upload_count > 0,
            has_extractions=len(visits) > 0,
            disclaimer=DISCLAIMER,
        )

    async def _process_one(
        self,
        db: AsyncSession,
        upload: UploadedFileRecord,
        patient_id: str | None,
    ) -> ProcessFileResult:
        path = self.upload_dir / upload.stored_filename
        if not path.exists():
            return ProcessFileResult(
                file_id=upload.id,
                filename=upload.original_filename,
                status="failed",
                error="Stored file missing on disk",
            )

        try:
            pdf_result = await self.pdf_service.extract(path)
        except PdfExtractionError as exc:
            return await self._save_failure(db, upload, patient_id, str(exc))

        if not pdf_result.full_text.strip():
            return await self._save_failure(
                db,
                upload,
                patient_id,
                "No text could be extracted (OCR may be required)",
            )

        try:
            extraction = await self.extraction_service.extract(pdf_result.full_text)
        except ExtractionError as exc:
            return await self._save_failure(db, upload, patient_id, str(exc))

        data = extraction.data
        pid = patient_id or _slug_patient_id(data.patient_name)
        visit_id = str(uuid.uuid4())
        record = VisitExtractionRecord(
            id=visit_id,
            patient_id=pid,
            source_file_id=upload.id,
            source_filename=upload.original_filename,
            visit_date=data.visit_date,
            patient_name=data.patient_name,
            hospital=data.hospital,
            doctor=data.doctor,
            status="completed",
            confidence_score=extraction.confidence.score,
            confidence_rationale=extraction.confidence.rationale,
            llm_provider=extraction.llm_provider,
            extraction_json=data.model_dump_json(),
            full_text=pdf_result.full_text,
        )
        db.add(record)
        await db.flush()

        return ProcessFileResult(
            file_id=upload.id,
            filename=upload.original_filename,
            status="completed",
            visit_id=visit_id,
            visit_date=data.visit_date,
            patient_name=data.patient_name,
            confidence=extraction.confidence,
            medicines_count=len(data.medicines),
            labs_count=len(data.lab_results),
        )

    async def _save_failure(
        self,
        db: AsyncSession,
        upload: UploadedFileRecord,
        patient_id: str | None,
        error: str,
    ) -> ProcessFileResult:
        visit_id = str(uuid.uuid4())
        record = VisitExtractionRecord(
            id=visit_id,
            patient_id=patient_id or DEFAULT_PATIENT_ID,
            source_file_id=upload.id,
            source_filename=upload.original_filename,
            status="failed",
            error_message=error,
            extraction_json="{}",
            full_text="",
        )
        db.add(record)
        await db.flush()
        return ProcessFileResult(
            file_id=upload.id,
            filename=upload.original_filename,
            status="failed",
            visit_id=visit_id,
            error=error,
        )

    async def _resolve_uploads(
        self,
        db: AsyncSession,
        file_ids: list[str] | None,
    ) -> list[UploadedFileRecord]:
        if file_ids:
            rows: list[UploadedFileRecord] = []
            for file_id in file_ids:
                row = await db.get(UploadedFileRecord, file_id)
                if row is not None:
                    rows.append(row)
            return rows

        result = await db.execute(
            select(UploadedFileRecord).order_by(UploadedFileRecord.uploaded_at.asc())
        )
        return list(result.scalars().all())

    async def _latest_patient_id(self, db: AsyncSession) -> str | None:
        result = await db.execute(
            select(VisitExtractionRecord)
            .where(VisitExtractionRecord.status == "completed")
            .order_by(VisitExtractionRecord.created_at.desc())
        )
        row = result.scalars().first()
        return row.patient_id if row else None

    def _to_visit_view(self, row: VisitExtractionRecord) -> TimelineVisitView:
        data = self._parse_extraction(row.extraction_json)
        summary_parts: list[str] = []
        if data.hospital:
            summary_parts.append(f"Hospital: {data.hospital}")
        if data.doctor:
            summary_parts.append(f"Doctor: {data.doctor}")
        if data.diagnosis:
            summary_parts.append("Diagnosis: " + ", ".join(data.diagnosis))
        if not summary_parts and row.source_filename:
            summary_parts.append(f"Extracted from {row.source_filename}")

        return TimelineVisitView(
            id=row.id,
            date=row.visit_date or (row.created_at.date().isoformat() if row.created_at else "Unknown"),
            type="Uploaded report",
            summary=" · ".join(summary_parts) if summary_parts else "Structured extraction complete.",
            diagnosis=list(data.diagnosis),
            medicines=list(data.medicines),
            labs=list(data.lab_results),
            allergies=list(data.allergies),
            hospital=row.hospital,
            doctor=row.doctor,
            source_file_id=row.source_file_id,
            source_filename=row.source_filename,
            confidence=ConfidenceScore(
                score=row.confidence_score,
                rationale=row.confidence_rationale,
            ),
        )

    @staticmethod
    def _parse_extraction(raw: str) -> MedicalExtraction:
        try:
            payload = json.loads(raw or "{}")
            return MedicalExtraction.model_validate(payload)
        except Exception:
            return MedicalExtraction()

    @staticmethod
    def _dedupe_medicines(medicines: list[Medicine]) -> list[Medicine]:
        seen: set[str] = set()
        unique: list[Medicine] = []
        for med in medicines:
            key = "|".join(
                [
                    (med.name or "").strip().lower(),
                    (med.dosage or "").strip().lower(),
                    (med.frequency or "").strip().lower(),
                ]
            )
            if not med.name or key in seen:
                continue
            seen.add(key)
            unique.append(med)
        return unique
