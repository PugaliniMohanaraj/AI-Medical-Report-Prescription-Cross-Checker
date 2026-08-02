import { useMemo, useState } from "react";

import { getErrorMessage } from "@/api/client";
import { analyzePrescription } from "@/api/endpoints";
import type { ConflictFinding, MedicineInput, SeveritySummary } from "@/types/api";
import { cn } from "@/utils/cn";

const SAMPLE_MEDICINES = `Metformin | 500mg | twice daily | 30 days
Metformin | 1000mg | twice daily | 30 days
Warfarin | 5mg | once daily |
Aspirin | 81mg | once daily |
Amoxicillin | 500mg | TID | 7 days`;

const SAMPLE_ALLERGIES = "Penicillin";

function parseMedicines(raw: string): MedicineInput[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, dosage, frequency, duration] = line.split("|").map((part) => part.trim());
      return {
        name: name || null,
        dosage: dosage || null,
        frequency: frequency || null,
        duration: duration || null,
      };
    })
    .filter((med) => med.name);
}

function severityStyles(severity: string): string {
  switch (severity) {
    case "High":
      return "border-red-200 bg-red-50 text-red-900";
    case "Medium":
      return "border-amber-200 bg-amber-50 text-amber-950";
    default:
      return "border-brand-100 bg-brand-50 text-brand-900";
  }
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        "rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wide",
        severity === "High" && "bg-red-600 text-white",
        severity === "Medium" && "bg-amber-500 text-white",
        severity === "Low" && "bg-brand-500 text-white",
      )}
    >
      {severity}
    </span>
  );
}

function SummaryStrip({ summary }: { summary: SeveritySummary }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[
        { label: "High", value: summary.high, className: "text-red-700" },
        { label: "Medium", value: summary.medium, className: "text-amber-700" },
        { label: "Low", value: summary.low, className: "text-brand-700" },
        { label: "Total", value: summary.total, className: "text-brand-900" },
      ].map((item) => (
        <div key={item.label} className="rounded-xl border border-brand-100 bg-white/80 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-brand-500">{item.label}</p>
          <p className={cn("font-display text-2xl font-semibold", item.className)}>{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function FindingCard({ finding }: { finding: ConflictFinding }) {
  return (
    <article className={cn("rounded-xl border p-4", severityStyles(finding.severity))}>
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={finding.severity} />
        <span className="rounded-md bg-white/70 px-2 py-0.5 text-xs font-medium capitalize">
          {finding.type.replaceAll("_", " ")}
        </span>
      </div>
      <h3 className="mt-2 font-display text-lg font-semibold">{finding.title}</h3>
      <p className="mt-2 text-sm leading-relaxed">{finding.explanation}</p>
      {finding.related_medicines.length > 0 && (
        <p className="mt-3 text-xs opacity-80">
          Medicines: {finding.related_medicines.join(", ")}
        </p>
      )}
      {!!finding.related_allergies?.length && (
        <p className="mt-1 text-xs opacity-80">
          Allergies: {finding.related_allergies.join(", ")}
        </p>
      )}
    </article>
  );
}

export function AnalysisPage() {
  const [medicinesText, setMedicinesText] = useState(SAMPLE_MEDICINES);
  const [allergiesText, setAllergiesText] = useState(SAMPLE_ALLERGIES);
  const [findings, setFindings] = useState<ConflictFinding[]>([]);
  const [summary, setSummary] = useState<SeveritySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allergies = useMemo(
    () =>
      allergiesText
        .split(/[\n,;]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    [allergiesText],
  );

  const onAnalyze = async () => {
    const medicines = parseMedicines(medicinesText);
    if (medicines.length === 0) {
      setError("Add at least one medicine (name | dosage | frequency | duration).");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await analyzePrescription({ medicines, allergies });
      setFindings(result.findings);
      setSummary(result.summary);
    } catch (err) {
      setFindings([]);
      setSummary(null);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="font-display text-3xl font-semibold text-brand-900">
          Prescription Analysis
        </h1>
        <p className="max-w-2xl text-brand-700/80">
          Detect duplicate medicines, dosage conflicts, allergy conflicts, and possible
          interactions. Every warning includes severity and a clinical explanation.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-brand-800">
            Medicines (one per line: name | dosage | frequency | duration)
          </span>
          <textarea
            value={medicinesText}
            onChange={(event) => setMedicinesText(event.target.value)}
            rows={10}
            className="w-full rounded-xl border border-brand-100 bg-white/80 px-3 py-2 font-mono text-sm text-brand-900 outline-none ring-brand-500 focus:ring-2"
          />
        </label>
        <label className="block space-y-2">
          <span className="text-sm font-medium text-brand-800">
            Allergies (comma or newline separated)
          </span>
          <textarea
            value={allergiesText}
            onChange={(event) => setAllergiesText(event.target.value)}
            rows={10}
            className="w-full rounded-xl border border-brand-100 bg-white/80 px-3 py-2 text-sm text-brand-900 outline-none ring-brand-500 focus:ring-2"
          />
        </label>
      </div>

      <button
        type="button"
        disabled={loading}
        onClick={() => void onAnalyze()}
        className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
      >
        {loading ? "Analyzing…" : "Analyze prescription"}
      </button>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {summary && <SummaryStrip summary={summary} />}

      {findings.length > 0 ? (
        <div className="space-y-3">
          <h2 className="font-display text-xl font-semibold text-brand-900">Warnings</h2>
          <div className="space-y-3">
            {findings.map((finding) => (
              <FindingCard
                key={`${finding.type}-${finding.title}-${finding.related_medicines.join("-")}`}
                finding={finding}
              />
            ))}
          </div>
        </div>
      ) : (
        summary && (
          <p className="rounded-xl border border-dashed border-brand-500/20 bg-white/60 px-4 py-8 text-center text-sm text-brand-500">
            No prescription warnings detected.
          </p>
        )
      )}
    </section>
  );
}
