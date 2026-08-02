"""Reference ranges and aliases for common laboratory tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabReference:
    canonical: str
    unit: str
    low: float | None
    high: float | None
    aliases: tuple[str, ...] = ()
    # If True, lower values are worse when falling; used for trend severity.
    higher_is_worse: bool = True


LAB_REFERENCES: list[LabReference] = [
    LabReference("hba1c", "%", 4.0, 5.6, ("hb a1c", "a1c", "glycated hemoglobin"), True),
    LabReference("glucose", "mg/dL", 70.0, 99.0, ("fasting glucose", "blood sugar", "fbs", "rbs"), True),
    LabReference("creatinine", "mg/dL", 0.6, 1.2, ("serum creatinine", "creat"), True),
    LabReference("egfr", "mL/min/1.73m2", 60.0, None, ("gfr", "estimated gfr"), False),
    LabReference("bun", "mg/dL", 7.0, 20.0, ("blood urea nitrogen", "urea nitrogen"), True),
    LabReference("hemoglobin", "g/dL", 12.0, 17.0, ("hb", "hgb", "haemoglobin"), False),
    LabReference("wbc", "x10^3/uL", 4.0, 11.0, ("white blood cell", "leukocytes"), True),
    LabReference("platelet", "x10^3/uL", 150.0, 450.0, ("plt", "platelets"), False),
    LabReference("sodium", "mEq/L", 135.0, 145.0, ("na", "na+"), True),
    LabReference("potassium", "mEq/L", 3.5, 5.0, ("k", "k+"), True),
    LabReference("alt", "U/L", 7.0, 56.0, ("sgpt", "alanine aminotransferase"), True),
    LabReference("ast", "U/L", 10.0, 40.0, ("sgot", "aspartate aminotransferase"), True),
    LabReference("total cholesterol", "mg/dL", None, 200.0, ("cholesterol", "tc"), True),
    LabReference("ldl", "mg/dL", None, 100.0, ("ldl-c", "ldl cholesterol"), True),
    LabReference("hdl", "mg/dL", 40.0, None, ("hdl-c", "hdl cholesterol"), False),
    LabReference("triglycerides", "mg/dL", None, 150.0, ("tg", "trigs"), True),
    LabReference("tsh", "mIU/L", 0.4, 4.0, ("thyroid stimulating hormone",), True),
    LabReference("vitamin d", "ng/mL", 30.0, 100.0, ("25-oh vitamin d", "vit d"), False),
    LabReference("crp", "mg/L", None, 3.0, ("c-reactive protein", "hs-crp"), True),
]


def normalize_test_name(name: str) -> str:
    return " ".join(name.lower().strip().replace("_", " ").replace("-", " ").split())


def resolve_reference(test_name: str) -> LabReference | None:
    key = normalize_test_name(test_name)

    # Prefer exact canonical / alias matches before substring heuristics.
    for ref in LAB_REFERENCES:
        if key == ref.canonical or key in ref.aliases:
            return ref

    for ref in LAB_REFERENCES:
        if ref.canonical in key or key in ref.canonical:
            return ref
        # Require alias token boundaries to avoid "hb" matching "hba1c"
        tokens = set(key.split())
        if any(alias in tokens or alias == key for alias in ref.aliases):
            return ref
    return None
