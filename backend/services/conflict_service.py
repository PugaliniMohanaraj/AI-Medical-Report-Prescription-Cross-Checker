"""Prescription conflict analysis: duplicates, dosage, allergies, interactions."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

from backend.models.schemas import (
    ConfidenceScore,
    ConflictFinding,
    Medicine,
    PrescriptionAnalysisRequest,
    PrescriptionAnalysisResponse,
    SeveritySummary,
)
from backend.services.drug_knowledge import (
    ALLERGY_CROSSWALK,
    CLASS_INTERACTIONS,
    DRUG_ALIASES,
    KNOWN_INTERACTIONS,
)

_DOSE_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|µg|g|ml|mL|iu|units|%|meq)?",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9\s\-+/]+")
_MULTISPACE = re.compile(r"\s+")

SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3}


@dataclass(slots=True)
class _NormalizedMed:
    index: int
    original_name: str
    canonical: str
    dosage_raw: str | None
    dose_value: float | None
    dose_unit: str | None
    frequency: str | None
    duration: str | None


class ConflictService:
    """Detect duplicate medicines, dosage conflicts, allergy conflicts, and interactions."""

    async def analyze(
        self,
        medicines: Sequence[Medicine] | Sequence[dict],
        allergies: Sequence[str] | None = None,
    ) -> PrescriptionAnalysisResponse:
        meds = [self._as_medicine(item) for item in medicines]
        allergy_list = [a for a in (allergies or []) if a and str(a).strip()]

        named = [m for m in meds if (m.name or "").strip()]
        normalized = [self._normalize_med(i, m) for i, m in enumerate(named)]

        findings: list[ConflictFinding] = []
        findings.extend(await self.detect_duplicates(normalized))
        findings.extend(await self.detect_dosage_conflicts(normalized))
        findings.extend(await self.detect_allergy_conflicts(normalized, allergy_list))
        findings.extend(await self.detect_interactions(normalized))

        findings = self._dedupe_findings(findings)
        findings.sort(
            key=lambda f: (-SEVERITY_RANK.get(f.severity, 0), f.type, f.title),
        )

        summary = SeveritySummary(
            low=sum(1 for f in findings if f.severity == "Low"),
            medium=sum(1 for f in findings if f.severity == "Medium"),
            high=sum(1 for f in findings if f.severity == "High"),
            total=len(findings),
        )

        return PrescriptionAnalysisResponse(
            findings=findings,
            summary=summary,
            medicines_analyzed=len(normalized),
            allergies_considered=len(allergy_list),
        )

    async def detect_duplicates(
        self,
        medicines: Sequence[_NormalizedMed] | list[dict],
    ) -> list[ConflictFinding]:
        normalized = self._ensure_normalized(medicines)
        groups: dict[str, list[_NormalizedMed]] = defaultdict(list)
        for med in normalized:
            if med.canonical:
                groups[med.canonical].append(med)

        findings: list[ConflictFinding] = []
        for canonical, group in groups.items():
            if len(group) < 2:
                continue
            names = [m.original_name for m in group]
            findings.append(
                ConflictFinding(
                    type="duplicate",
                    severity="Medium",
                    title=f"Duplicate medicine: {canonical}",
                    explanation=(
                        f"'{canonical}' appears {len(group)} times in the prescription "
                        f"({', '.join(names)}). Duplicate entries can lead to unintended "
                        "double dosing if both are dispensed or administered."
                    ),
                    related_medicines=names,
                    related_allergies=[],
                    confidence=ConfidenceScore(
                        score=0.95,
                        rationale="Exact/alias-normalized name match across multiple entries.",
                    ),
                )
            )
        return findings

    async def detect_dosage_conflicts(
        self,
        medicines: Sequence[_NormalizedMed] | list[dict],
    ) -> list[ConflictFinding]:
        normalized = self._ensure_normalized(medicines)
        groups: dict[str, list[_NormalizedMed]] = defaultdict(list)
        for med in normalized:
            if med.canonical:
                groups[med.canonical].append(med)

        findings: list[ConflictFinding] = []
        for canonical, group in groups.items():
            if len(group) < 2:
                continue

            dose_signatures = {
                (
                    None if m.dose_value is None else round(m.dose_value, 4),
                    (m.dose_unit or "").lower() or None,
                    (m.frequency or "").strip().lower() or None,
                )
                for m in group
            }
            # Only flag when at least two entries expose conflicting dose/frequency details.
            concrete = [sig for sig in dose_signatures if sig[0] is not None or sig[2]]
            if len(concrete) < 2:
                continue

            values = sorted({sig for sig in concrete})
            if len(values) < 2:
                continue

            names = [m.original_name for m in group]
            details = "; ".join(
                self._dose_description(m) for m in group
            )
            severity = "High" if self._has_numeric_dose_mismatch(group) else "Medium"
            findings.append(
                ConflictFinding(
                    type="dosage_conflict",
                    severity=severity,
                    title=f"Dosage conflict for {canonical}",
                    explanation=(
                        f"Multiple prescriptions for '{canonical}' specify different dosing instructions "
                        f"({details}). Conflicting directions increase the risk of under- or overdosing."
                    ),
                    related_medicines=names,
                    related_allergies=[],
                    confidence=ConfidenceScore(
                        score=0.9 if severity == "High" else 0.8,
                        rationale="Compared parsed dose amounts and/or free-text frequency strings.",
                    ),
                )
            )
        return findings

    async def detect_allergy_conflicts(
        self,
        medicines: Sequence[_NormalizedMed] | list[dict],
        allergies: Sequence[str],
    ) -> list[ConflictFinding]:
        normalized = self._ensure_normalized(medicines)
        findings: list[ConflictFinding] = []
        if not allergies:
            return findings

        for allergy in allergies:
            allergy_key = self._normalize_name(allergy)
            risky_drugs = self._allergy_risk_set(allergy_key)
            for med in normalized:
                if med.canonical in risky_drugs or self._names_overlap(med.canonical, allergy_key):
                    findings.append(
                        ConflictFinding(
                            type="allergy_conflict",
                            severity="High",
                            title=f"Allergy conflict: {med.original_name}",
                            explanation=(
                                f"Patient allergy list includes '{allergy}', which is linked to "
                                f"'{med.original_name}' (normalized as '{med.canonical}'). "
                                "Administering this medicine may trigger a hypersensitivity reaction "
                                "and usually warrants an alternative agent and clinical review."
                            ),
                            related_medicines=[med.original_name],
                            related_allergies=[allergy],
                            confidence=ConfidenceScore(
                                score=0.92,
                                rationale="Matched allergy label to medicine via alias/cross-reactivity map.",
                            ),
                        )
                    )
        return findings

    async def detect_interactions(
        self,
        medicines: Sequence[_NormalizedMed] | list[dict],
    ) -> list[ConflictFinding]:
        normalized = self._ensure_normalized(medicines)
        findings: list[ConflictFinding] = []
        seen_pairs: set[frozenset[str]] = set()

        for i, left in enumerate(normalized):
            for right in normalized[i + 1 :]:
                if not left.canonical or not right.canonical:
                    continue
                if left.canonical == right.canonical:
                    continue
                pair = frozenset({left.canonical, right.canonical})
                if pair in seen_pairs:
                    continue

                hit = KNOWN_INTERACTIONS.get(pair)
                if hit is None:
                    hit = self._class_interaction(left.canonical, right.canonical)
                if hit is None:
                    continue

                severity, explanation = hit
                seen_pairs.add(pair)
                findings.append(
                    ConflictFinding(
                        type="interaction",
                        severity=severity,
                        title=f"Possible interaction: {left.original_name} + {right.original_name}",
                        explanation=explanation,
                        related_medicines=[left.original_name, right.original_name],
                        related_allergies=[],
                        confidence=ConfidenceScore(
                            score=0.85 if severity == "High" else 0.75,
                            rationale="Matched curated interaction knowledge base / drug-class rules.",
                        ),
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_normalized(
        self,
        medicines: Sequence[_NormalizedMed] | list[dict] | Sequence[Medicine],
    ) -> list[_NormalizedMed]:
        if not medicines:
            return []
        if isinstance(medicines[0], _NormalizedMed):
            return list(medicines)  # type: ignore[arg-type]
        return [
            self._normalize_med(i, self._as_medicine(item))
            for i, item in enumerate(medicines)
            if self._as_medicine(item).name
        ]

    @staticmethod
    def _as_medicine(item: Medicine | dict) -> Medicine:
        if isinstance(item, Medicine):
            return item
        return Medicine.model_validate(item)

    def _normalize_med(self, index: int, med: Medicine) -> _NormalizedMed:
        original = (med.name or "").strip()
        canonical = self.canonicalize_drug(original)
        dose_value, dose_unit = self._parse_dose(med.dosage)
        return _NormalizedMed(
            index=index,
            original_name=original,
            canonical=canonical,
            dosage_raw=med.dosage,
            dose_value=dose_value,
            dose_unit=dose_unit,
            frequency=med.frequency,
            duration=med.duration,
        )

    def canonicalize_drug(self, name: str) -> str:
        cleaned = self._normalize_name(name)
        if not cleaned:
            return ""

        # Direct canonical hit
        if cleaned in DRUG_ALIASES:
            return cleaned

        # Alias -> canonical
        for canonical, aliases in DRUG_ALIASES.items():
            if cleaned in aliases:
                return canonical
            if cleaned.startswith(canonical + " ") or cleaned.startswith(canonical + "-"):
                return canonical

        # Allergy-style multiword labels already normalized
        return cleaned

    def _allergy_risk_set(self, allergy_key: str) -> set[str]:
        risky: set[str] = set()
        for label, drugs in ALLERGY_CROSSWALK.items():
            if allergy_key == label or label in allergy_key or allergy_key in label:
                risky |= {self.canonicalize_drug(d) for d in drugs}
                risky.add(label)
        # Also treat the allergy itself as a drug name if listed.
        risky.add(self.canonicalize_drug(allergy_key))
        return {d for d in risky if d}

    def _class_interaction(self, left: str, right: str) -> tuple[str, str] | None:
        for set_a, set_b, severity, explanation in CLASS_INTERACTIONS:
            if (left in set_a and right in set_b) or (left in set_b and right in set_a):
                return severity, explanation
        return None

    @staticmethod
    def _normalize_name(name: str) -> str:
        text = name.lower().strip()
        text = text.replace("µ", "u")
        text = _NON_ALNUM.sub(" ", text)
        text = _MULTISPACE.sub(" ", text).strip()
        # Drop common salt/formulation suffixes for matching
        for token in (
            " hydrochloride",
            " hcl",
            " sodium",
            " potassium",
            " tablet",
            " tablets",
            " capsule",
            " capsules",
            " xr",
            " er",
            " sr",
            " cr",
        ):
            if text.endswith(token):
                text = text[: -len(token)].strip()
        return text

    @staticmethod
    def _parse_dose(dosage: str | None) -> tuple[float | None, str | None]:
        if not dosage:
            return None, None
        match = _DOSE_RE.search(dosage)
        if not match:
            return None, None
        value = float(match.group("value"))
        unit = match.group("unit")
        return value, (unit.lower() if unit else None)

    @staticmethod
    def _dose_description(med: _NormalizedMed) -> str:
        parts = [med.original_name]
        if med.dosage_raw:
            parts.append(f"dose={med.dosage_raw}")
        if med.frequency:
            parts.append(f"freq={med.frequency}")
        return " ".join(parts)

    @staticmethod
    def _has_numeric_dose_mismatch(group: Iterable[_NormalizedMed]) -> bool:
        numeric = [
            (m.dose_value, (m.dose_unit or "").lower())
            for m in group
            if m.dose_value is not None
        ]
        if len(numeric) < 2:
            return False
        return len(set(numeric)) > 1

    @staticmethod
    def _names_overlap(left: str, right: str) -> bool:
        if not left or not right:
            return False
        return left == right or left in right or right in left

    @staticmethod
    def _dedupe_findings(findings: list[ConflictFinding]) -> list[ConflictFinding]:
        seen: set[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = set()
        unique: list[ConflictFinding] = []
        for finding in findings:
            key = (
                finding.type,
                finding.title.lower(),
                tuple(sorted(m.lower() for m in finding.related_medicines)),
                tuple(sorted(a.lower() for a in finding.related_allergies)),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(finding)
        return unique
