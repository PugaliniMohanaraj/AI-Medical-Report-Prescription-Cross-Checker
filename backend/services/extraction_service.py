"""AI-based medical information extraction into structured JSON."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from backend.models.schemas import (
    ConfidenceScore,
    MedicalExtraction,
    MedicalExtractionResponse,
)
from backend.utils.config import Settings, get_settings
from backend.utils.llm import LLMClient, LLMError, get_llm_client

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

SYSTEM_PROMPT = """You are a careful medical information extraction engine.
Extract only facts explicitly present in the provided clinical text.
Do not invent values. If a field is missing or unclear, use null or an empty list.
Return ONLY a single JSON object (no markdown, no commentary) with exactly these keys:

{
  "patient_name": string | null,
  "hospital": string | null,
  "doctor": string | null,
  "visit_date": string | null,
  "diagnosis": string[] ,
  "medicines": [
    {
      "name": string | null,
      "dosage": string | null,
      "frequency": string | null,
      "duration": string | null
    }
  ],
  "allergies": string[],
  "lab_results": [
    {
      "test_name": string | null,
      "value": string | null,
      "unit": string | null,
      "reference_range": string | null,
      "status": string | null
    }
  ],
  "vital_signs": [
    {
      "name": string | null,
      "value": string | null,
      "unit": string | null
    }
  ]
}

Rules:
- Put each medicine's dosage, frequency, and duration on that medicine object.
- diagnosis and allergies are arrays of strings.
- visit_date should keep the date as written in the source when possible (ISO 8601 preferred).
- vital_signs examples: Blood Pressure, Heart Rate, Temperature, SpO2, Respiratory Rate, Weight, Height.
"""


class ExtractionError(Exception):
    """Raised when structured extraction fails."""


class ExtractionService:
    """Convert free-text medical reports into structured JSON via LLM."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or get_llm_client(self.settings)

    async def extract(self, text: str) -> MedicalExtractionResponse:
        """Extract structured medical fields from raw text."""
        cleaned = (text or "").strip()
        if not cleaned:
            raise ExtractionError("Input text is empty")

        user_prompt = (
            "Extract structured medical information from the following text.\n\n"
            f"--- BEGIN MEDICAL TEXT ---\n{cleaned}\n--- END MEDICAL TEXT ---"
        )

        try:
            raw = await self.llm.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                json_mode=True,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
        except LLMError as exc:
            raise ExtractionError(str(exc)) from exc

        try:
            payload = self._parse_json(raw)
            data = MedicalExtraction.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            logger.warning("Failed to parse LLM extraction output: %s", exc)
            raise ExtractionError(
                "Model returned invalid structured JSON for medical extraction"
            ) from exc

        confidence = self._estimate_confidence(data, cleaned)
        return MedicalExtractionResponse(
            data=data,
            confidence=confidence,
            llm_provider=self.llm.provider_name,
            source="text",
        )

    async def to_structured_json(self, text: str) -> dict[str, Any]:
        """Compatibility helper returning a plain dict."""
        result = await self.extract(text)
        return result.model_dump(mode="json")

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        fence = _JSON_FENCE_RE.search(text)
        if fence:
            text = fence.group(1).strip()

        # Prefer the outermost object if the model adds chatter.
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("No JSON object found in model output")
            text = text[start : end + 1]

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        return data

    @staticmethod
    def _estimate_confidence(data: MedicalExtraction, source_text: str) -> ConfidenceScore:
        """Heuristic confidence until a calibrated scorer is added."""
        filled = 0
        total = 9

        if data.patient_name:
            filled += 1
        if data.hospital:
            filled += 1
        if data.doctor:
            filled += 1
        if data.visit_date:
            filled += 1
        if data.diagnosis:
            filled += 1
        if data.medicines:
            filled += 1
        if data.allergies:
            filled += 1
        if data.lab_results:
            filled += 1
        if data.vital_signs:
            filled += 1

        density = min(1.0, len(source_text) / 800)
        score = round(0.35 + (0.5 * (filled / total)) + (0.15 * density), 3)
        score = max(0.0, min(1.0, score))

        return ConfidenceScore(
            score=score,
            rationale=(
                f"Filled {filled}/{total} top-level clinical field groups "
                f"from {len(source_text)} characters of source text."
            ),
        )
