"""Lab result trend analysis across visits."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Sequence

from backend.models.schemas import (
    ConfidenceScore,
    LabChartSeries,
    LabDataPoint,
    LabTrendRequest,
    LabTrendResponse,
    LabTrendSeries,
    LabVisitInput,
)
from backend.services.lab_reference import LabReference, normalize_test_name, resolve_reference
from backend.utils.config import Settings, get_settings
from backend.utils.llm import LLMClient, LLMError, get_llm_client

logger = logging.getLogger(__name__)

_VALUE_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

SYSTEM_PROMPT = """You are a clinical lab interpretation assistant.
Given structured lab trend summaries, write a concise explanation (3-6 sentences) for a clinician.
Focus on abnormal trends, direction of change, and clinical relevance.
Do not invent values that are not provided. Avoid definitive diagnoses; suggest monitoring or follow-up when appropriate.
Return plain text only (no markdown headings)."""


class LabService:
    """Compare lab values across visits, flag abnormal trends, and explain with AI."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._llm = llm

    async def analyze(
        self,
        request: LabTrendRequest,
        *,
        include_ai_explanation: bool | None = None,
    ) -> LabTrendResponse:
        include_ai = (
            self.settings.lab_ai_explanations_enabled
            if include_ai_explanation is None
            else include_ai_explanation
        )
        if request.include_ai_explanation is False:
            include_ai = False

        visits = self._sorted_visits(request.visits)
        series = self._build_series(visits)
        abnormal = [s for s in series if s.is_abnormal_trend]

        ai_text: str | None = None
        provider: str | None = None
        confidence = ConfidenceScore(
            score=0.7,
            rationale="Rule-based trend analysis from cross-visit lab values.",
        )

        if include_ai and series:
            try:
                ai_text, provider = await self._generate_ai_explanation(series, abnormal)
                confidence = ConfidenceScore(
                    score=0.86,
                    rationale="Rule-based trends enriched with LLM narrative explanation.",
                )
            except Exception as exc:  # noqa: BLE001 — fall back to heuristic text
                logger.warning("Lab AI explanation failed: %s", exc)
                ai_text = self._heuristic_explanation(series, abnormal)
                confidence = ConfidenceScore(
                    score=0.72,
                    rationale="AI explanation unavailable; returned heuristic narrative.",
                )
        elif series:
            ai_text = self._heuristic_explanation(series, abnormal)

        charts = [
            LabChartSeries(
                test_name=s.test_name,
                unit=s.unit,
                reference_low=s.reference_low,
                reference_high=s.reference_high,
                is_abnormal_trend=s.is_abnormal_trend,
                severity=s.severity,
                data=[
                    {
                        "date": p.visit_date,
                        "value": p.value,
                        "abnormal": p.is_abnormal,
                        "status": p.status,
                        "visit_id": p.visit_id,
                    }
                    for p in s.points
                ],
            )
            for s in series
        ]

        return LabTrendResponse(
            patient_id=request.patient_id,
            visit_count=len(visits),
            series=series,
            abnormal_trends=abnormal,
            charts=charts,
            ai_explanation=ai_text,
            confidence=confidence,
            llm_provider=provider,
        )

    async def compute_trends(self, lab_history: list[dict[str, Any]]) -> dict[str, Any]:
        """Compatibility helper accepting loosely structured visit dicts."""
        visits = [LabVisitInput.model_validate(item) for item in lab_history]
        result = await self.analyze(LabTrendRequest(visits=visits))
        return result.model_dump(mode="json")

    def _build_series(self, visits: list[LabVisitInput]) -> list[LabTrendSeries]:
        buckets: dict[str, list[tuple[LabVisitInput, Any, LabReference | None, float, str]]] = defaultdict(
            list
        )

        for visit in visits:
            for lab in visit.labs:
                name = (lab.test_name or "").strip()
                if not name:
                    continue
                numeric = self._parse_numeric(lab.value)
                if numeric is None:
                    continue
                ref = resolve_reference(name)
                key = ref.canonical if ref is not None else normalize_test_name(name)
                buckets[key].append((visit, lab, ref, numeric, name))

        series_list: list[LabTrendSeries] = []
        for _key, rows in buckets.items():
            rows_sorted = sorted(rows, key=lambda item: self._parse_date(item[0].visit_date) or datetime.min)
            display_name = rows_sorted[-1][4]
            ref = next((r for _, _, r, _, _ in rows_sorted if r is not None), None)
            unit = next(
                (
                    (lab.unit or (ref.unit if ref else None))
                    for _, lab, ref, _, _ in rows_sorted
                    if (lab.unit or (ref.unit if ref else None))
                ),
                ref.unit if ref else None,
            )
            ref_range = next(
                (lab.reference_range for _, lab, _, _, _ in rows_sorted if lab.reference_range),
                self._format_ref_range(ref),
            )
            low = ref.low if ref else None
            high = ref.high if ref else None

            # Prefer explicit reference_range parsing when present
            parsed_low, parsed_high = self._parse_reference_range(
                next((lab.reference_range for _, lab, _, _, _ in rows_sorted if lab.reference_range), None)
            )
            if parsed_low is not None or parsed_high is not None:
                low = parsed_low if parsed_low is not None else low
                high = parsed_high if parsed_high is not None else high

            points: list[LabDataPoint] = []
            for visit, lab, _, numeric, _name in rows_sorted:
                status = self._status_for_value(numeric, low, high, lab.status)
                points.append(
                    LabDataPoint(
                        visit_id=visit.visit_id,
                        visit_date=visit.visit_date,
                        value=numeric,
                        unit=lab.unit or unit,
                        status=status,
                        is_abnormal=status in {"high", "low"},
                    )
                )

            direction, percent_change = self._direction(points)
            is_abnormal_trend, severity, summary = self._assess_trend(
                display_name, points, direction, percent_change, ref
            )

            series_list.append(
                LabTrendSeries(
                    test_name=display_name,
                    unit=unit,
                    reference_range=ref_range,
                    reference_low=low,
                    reference_high=high,
                    points=points,
                    direction=direction,
                    percent_change=percent_change,
                    is_abnormal_trend=is_abnormal_trend,
                    severity=severity,
                    trend_summary=summary,
                )
            )

        series_list.sort(
            key=lambda s: (
                0 if s.is_abnormal_trend else 1,
                {"High": 0, "Medium": 1, "Low": 2, "None": 3}.get(s.severity, 9),
                s.test_name.lower(),
            )
        )
        return series_list

    async def _generate_ai_explanation(
        self,
        series: list[LabTrendSeries],
        abnormal: list[LabTrendSeries],
    ) -> tuple[str, str]:
        llm = self._llm or get_llm_client(self.settings)
        payload = {
            "abnormal_count": len(abnormal),
            "trends": [
                {
                    "test_name": s.test_name,
                    "unit": s.unit,
                    "direction": s.direction,
                    "percent_change": s.percent_change,
                    "severity": s.severity,
                    "is_abnormal_trend": s.is_abnormal_trend,
                    "reference_range": s.reference_range,
                    "values": [
                        {
                            "date": p.visit_date,
                            "value": p.value,
                            "status": p.status,
                        }
                        for p in s.points
                    ],
                    "summary": s.trend_summary,
                }
                for s in series
            ],
        }
        user_prompt = (
            "Explain these cross-visit laboratory trends for a clinical dashboard.\n"
            f"Structured data:\n{payload}"
        )
        try:
            text = await llm.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=700,
                json_mode=False,
            )
        except LLMError:
            raise
        return text.strip(), llm.provider_name

    def _heuristic_explanation(
        self,
        series: list[LabTrendSeries],
        abnormal: list[LabTrendSeries],
    ) -> str:
        if not series:
            return "No numeric lab values were available to analyze across visits."
        if not abnormal:
            return (
                f"Reviewed {len(series)} lab marker(s) across visits. "
                "No clearly abnormal worsening trends were detected based on available "
                "reference ranges and point-to-point changes."
            )
        parts = [
            f"Identified {len(abnormal)} abnormal lab trend(s) across visits:",
        ]
        for item in abnormal[:6]:
            parts.append(f"- {item.test_name}: {item.trend_summary}")
        if len(abnormal) > 6:
            parts.append(f"- …and {len(abnormal) - 6} more.")
        parts.append("Consider clinical correlation and confirmatory testing where indicated.")
        return "\n".join(parts)

    def _assess_trend(
        self,
        test_name: str,
        points: list[LabDataPoint],
        direction: str,
        percent_change: float | None,
        ref: LabReference | None,
    ) -> tuple[bool, str, str]:
        if len(points) < 2:
            status = points[0].status if points else "unknown"
            abnormal = status in {"high", "low"}
            severity = "Medium" if abnormal else "None"
            summary = (
                f"Only one value available ({points[0].value}{self._unit_suffix(points[0].unit)}); "
                f"status={status}."
                if points
                else "No values."
            )
            return abnormal, severity, summary

        first, last = points[0], points[-1]
        out_of_range_count = sum(1 for p in points if p.is_abnormal)
        crossed_into_abnormal = (not first.is_abnormal) and last.is_abnormal
        worsening = False
        if ref is not None and percent_change is not None:
            if ref.higher_is_worse and direction == "rising" and (last.is_abnormal or percent_change >= 15):
                worsening = True
            if (not ref.higher_is_worse) and direction == "falling" and (
                last.is_abnormal or abs(percent_change) >= 15
            ):
                worsening = True
        elif percent_change is not None and abs(percent_change) >= 20 and last.is_abnormal:
            worsening = True

        is_abnormal = bool(out_of_range_count >= 1 or crossed_into_abnormal or worsening)
        if crossed_into_abnormal or (worsening and last.is_abnormal):
            severity = "High"
        elif worsening or out_of_range_count >= 2:
            severity = "Medium"
        elif is_abnormal:
            severity = "Low"
        else:
            severity = "None"

        change_txt = (
            f"{percent_change:+.1f}% from {first.value} to {last.value}"
            if percent_change is not None
            else f"from {first.value} to {last.value}"
        )
        summary = (
            f"{direction.replace('_', ' ').title()} trend {change_txt}"
            f"{self._unit_suffix(last.unit)} over {len(points)} visits; "
            f"latest status={last.status}."
        )
        if is_abnormal:
            summary += " Marked as an abnormal trend requiring attention."
        return is_abnormal, severity, summary

    @staticmethod
    def _direction(points: list[LabDataPoint]) -> tuple[str, float | None]:
        if len(points) < 2:
            return "insufficient_data", None
        first = points[0].value
        last = points[-1].value
        if first == 0:
            percent = None
        else:
            percent = round(((last - first) / abs(first)) * 100.0, 2)

        delta = last - first
        threshold = max(0.05 * abs(first), 1e-6)
        if abs(delta) <= threshold:
            return "stable", percent
        if delta > 0:
            return "rising", percent
        return "falling", percent

    @staticmethod
    def _status_for_value(
        value: float,
        low: float | None,
        high: float | None,
        explicit: str | None,
    ) -> str:
        if explicit:
            normalized = explicit.strip().lower()
            if normalized in {"high", "h", "above"}:
                return "high"
            if normalized in {"low", "l", "below"}:
                return "low"
            if normalized in {"normal", "n", "within"}:
                return "normal"
        if low is not None and value < low:
            return "low"
        if high is not None and value > high:
            return "high"
        if low is not None or high is not None:
            return "normal"
        return "unknown"

    @staticmethod
    def _parse_numeric(value: str | float | int | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        match = _VALUE_RE.search(str(value).replace(",", ""))
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    @staticmethod
    def _parse_reference_range(text: str | None) -> tuple[float | None, float | None]:
        if not text:
            return None, None
        cleaned = text.replace(",", " ").strip().lower()
        # patterns: 4.0-5.6, 70 – 99, <200, >40, <=100
        between = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*[-–to]+\s*([-+]?\d+(?:\.\d+)?)",
            cleaned,
        )
        if between:
            return float(between.group(1)), float(between.group(2))
        lt = re.search(r"(?:<|<=)\s*([-+]?\d+(?:\.\d+)?)", cleaned)
        if lt:
            return None, float(lt.group(1))
        gt = re.search(r"(?:>|>=)\s*([-+]?\d+(?:\.\d+)?)", cleaned)
        if gt:
            return float(gt.group(1)), None
        return None, None

    @staticmethod
    def _format_ref_range(ref: LabReference | None) -> str | None:
        if ref is None:
            return None
        if ref.low is not None and ref.high is not None:
            return f"{ref.low}-{ref.high} {ref.unit}"
        if ref.low is not None:
            return f">={ref.low} {ref.unit}"
        if ref.high is not None:
            return f"<={ref.high} {ref.unit}"
        return None

    @staticmethod
    def _unit_suffix(unit: str | None) -> str:
        return f" {unit}" if unit else ""

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _sorted_visits(self, visits: Sequence[LabVisitInput]) -> list[LabVisitInput]:
        return sorted(
            visits,
            key=lambda v: self._parse_date(v.visit_date) or datetime.min,
        )
