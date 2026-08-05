import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

import { getErrorMessage } from "@/api/client";
import { analyzePrescription } from "@/api/endpoints";
import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { usePatient } from "@/hooks/usePatient";
import type { ConflictFinding, SeveritySummary } from "@/types/api";
import { cn } from "@/utils/cn";

export function WarningsPage() {
  const { overview, loading: patientLoading } = usePatient();
  const [findings, setFindings] = useState<ConflictFinding[]>([]);
  const [summary, setSummary] = useState<SeveritySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const medicines = overview?.medicines ?? [];
    if (!medicines.length) {
      setFindings(overview?.findings ?? []);
      setSummary(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzePrescription({
        medicines,
        allergies: overview?.allergies ?? [],
      });
      setFindings(result.findings);
      setSummary(result.summary);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!patientLoading) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientLoading, overview?.patient_id, overview?.medicines?.length]);

  const highRisk = findings.some((f) => f.severity === "High");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warnings"
        description="Duplicate medicines, dosage conflicts, allergy conflicts, and possible interactions from uploaded reports."
        actions={
          <button type="button" className="btn-primary" disabled={loading} onClick={() => void load()}>
            {loading ? "Scanning…" : "Re-scan regimen"}
          </button>
        }
      />

      <MedicalDisclaimer text={overview?.disclaimer} />
      {highRisk && (
        <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
          High-risk findings detected. Consult a doctor or pharmacist before changing any medicines.
        </div>
      )}

      {summary && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="High" value={summary.high} tone="danger" />
          <StatCard label="Medium" value={summary.medium} tone="warning" />
          <StatCard label="Low" value={summary.low} tone="success" />
          <StatCard label="Total" value={summary.total} />
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100">
          {error}
        </div>
      )}

      <Panel title="Safety findings">
        {!overview?.has_extractions ? (
          <div className="space-y-3">
            <p className="text-sm text-surface-500">Upload and analyze reports to generate warnings.</p>
            <Link to="/uploads" className="btn-primary inline-flex">
              Go to uploads
            </Link>
          </div>
        ) : findings.length === 0 ? (
          <p className="text-sm text-surface-500">No warnings detected for the current regimen.</p>
        ) : (
          <div className="space-y-3">
            {findings.map((finding) => (
              <article
                key={`${finding.type}-${finding.title}-${finding.related_medicines.join("-")}`}
                className={cn(
                  "rounded-2xl border p-4",
                  finding.severity === "High" && "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30",
                  finding.severity === "Medium" && "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
                  finding.severity === "Low" && "border-brand-100 bg-brand-50 dark:border-brand-800 dark:bg-brand-950/30",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-surface-900 px-2 py-0.5 text-[11px] font-semibold uppercase text-white dark:bg-white dark:text-surface-900">
                    {finding.severity}
                  </span>
                  <span className="text-xs capitalize text-surface-500">
                    {finding.type.replaceAll("_", " ")}
                  </span>
                </div>
                <h3 className="mt-2 font-display text-lg font-semibold">{finding.title}</h3>
                <p className="mt-2 text-sm leading-relaxed">{finding.explanation}</p>
                {finding.related_medicines.length > 0 && (
                  <p className="mt-3 text-xs text-surface-500">
                    Medicines: {finding.related_medicines.join(", ")}
                  </p>
                )}
              </article>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
