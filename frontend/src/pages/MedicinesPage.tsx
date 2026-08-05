import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { analyzePrescription } from "@/api/endpoints";
import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { usePatient } from "@/hooks/usePatient";
import type { ConflictFinding, MedicineInput, SeveritySummary } from "@/types/api";
import { cn } from "@/utils/cn";

function parseMedicines(raw: string): MedicineInput[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, dosage, frequency, duration] = line.split("|").map((part) => part.trim());
      return { name: name || null, dosage: dosage || null, frequency: frequency || null, duration: duration || null };
    })
    .filter((med) => med.name);
}

function medicinesToText(meds: MedicineInput[]) {
  return meds
    .map((m) => [m.name, m.dosage, m.frequency, m.duration].filter(Boolean).join(" | "))
    .join("\n");
}

export function MedicinesPage() {
  const { overview } = usePatient();
  const [medicinesText, setMedicinesText] = useState("");
  const [allergiesText, setAllergiesText] = useState("");
  const [findings, setFindings] = useState<ConflictFinding[]>([]);
  const [summary, setSummary] = useState<SeveritySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!overview) return;
    setMedicinesText(medicinesToText(overview.medicines));
    setAllergiesText(overview.allergies.join(", "));
    setFindings(overview.findings);
  }, [overview]);

  const latest = overview?.visits?.[overview.visits.length - 1];
  const allergies = useMemo(
    () => allergiesText.split(/[\n,;]+/).map((item) => item.trim()).filter(Boolean),
    [allergiesText],
  );

  const onAnalyze = async () => {
    const medicines = parseMedicines(medicinesText);
    if (!medicines.length) {
      setError("Add at least one medicine.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzePrescription({ medicines, allergies });
      setFindings(result.findings);
      setSummary(result.summary);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Medicines"
        description="Review the regimen extracted from uploaded reports and run prescription safety analysis."
        actions={
          <button type="button" className="btn-primary" disabled={loading} onClick={() => void onAnalyze()}>
            {loading ? "Analyzing…" : "Analyze regimen"}
          </button>
        }
      />

      <MedicalDisclaimer text={overview?.disclaimer} />

      {!overview?.has_extractions && (
        <Panel>
          <p className="text-sm text-surface-500">No medicines extracted yet.</p>
          <Link to="/uploads" className="btn-primary mt-4 inline-flex">
            Upload reports
          </Link>
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Extracted regimen" description={latest?.date || "From uploaded visits"}>
          <ul className="divide-y divide-surface-200 dark:divide-surface-700">
            {(overview?.medicines ?? []).map((med) => (
              <li key={`${med.name}-${med.dosage}`} className="flex items-start justify-between gap-3 py-3">
                <div>
                  <p className="font-medium">{med.name}</p>
                  <p className="text-xs text-surface-500">
                    {[med.dosage, med.frequency, med.duration].filter(Boolean).join(" · ")}
                  </p>
                </div>
              </li>
            ))}
            {!overview?.medicines?.length && (
              <li className="py-3 text-sm text-surface-500">No medicines available.</li>
            )}
          </ul>
        </Panel>

        <Panel title="Editable analysis input">
          <label className="block space-y-2">
            <span className="text-xs font-medium uppercase tracking-wide text-surface-500">Medicines</span>
            <textarea className="field min-h-40 font-mono" value={medicinesText} onChange={(e) => setMedicinesText(e.target.value)} />
          </label>
          <label className="mt-4 block space-y-2">
            <span className="text-xs font-medium uppercase tracking-wide text-surface-500">Allergies</span>
            <textarea className="field min-h-20" value={allergiesText} onChange={(e) => setAllergiesText(e.target.value)} />
          </label>
        </Panel>
      </div>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100">{error}</div>}

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["High", summary.high, "text-red-600"] as const,
            ["Medium", summary.medium, "text-amber-600"] as const,
            ["Low", summary.low, "text-brand-500"] as const,
            ["Total", summary.total, "text-surface-900 dark:text-surface-50"] as const,
          ].map(([label, value, color]) => (
            <div key={label} className="rounded-2xl border border-surface-200 bg-white/80 px-4 py-3 dark:border-surface-700 dark:bg-surface-900/70">
              <p className="text-xs uppercase text-surface-500">{label}</p>
              <p className={cn("font-display text-2xl font-semibold", color)}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {findings.length > 0 && (
        <Panel title="Detected issues">
          <div className="space-y-3">
            {findings.map((finding) => (
              <article
                key={`${finding.type}-${finding.title}`}
                className={cn(
                  "rounded-xl border p-4",
                  finding.severity === "High" && "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30",
                  finding.severity === "Medium" && "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
                  finding.severity === "Low" && "border-brand-100 bg-brand-50 dark:border-brand-800 dark:bg-brand-950/30",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-surface-900 px-2 py-0.5 text-[11px] font-semibold uppercase text-white dark:bg-surface-100 dark:text-surface-900">
                    {finding.severity}
                  </span>
                  <span className="text-xs capitalize text-surface-500">{finding.type.replaceAll("_", " ")}</span>
                </div>
                <h3 className="mt-2 font-semibold">{finding.title}</h3>
                <p className="mt-1 text-sm leading-relaxed">{finding.explanation}</p>
              </article>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
