import { Link } from "react-router-dom";

import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { usePatient } from "@/hooks/usePatient";

export function TimelinePage() {
  const { overview, loading, error } = usePatient();
  const visits = [...(overview?.visits ?? [])].reverse();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Timeline"
        description="Chronological clinical encounters merged from uploaded reports and structured extraction."
      />
      <MedicalDisclaimer text={overview?.disclaimer} />

      {loading && <p className="text-sm text-surface-500">Loading patient timeline…</p>}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100">
          {error}
        </div>
      )}

      {!loading && visits.length === 0 && (
        <Panel>
          <p className="text-sm text-surface-600 dark:text-surface-300">
            No extracted visits yet. Upload reports and wait for AI analysis to build the timeline.
          </p>
          <Link to="/uploads" className="btn-primary mt-4 inline-flex">
            Go to uploads
          </Link>
        </Panel>
      )}

      <div className="relative space-y-4 before:absolute before:bottom-3 before:left-[1.15rem] before:top-3 before:w-px before:bg-brand-200 dark:before:bg-brand-700/50">
        {visits.map((visit) => (
          <article key={visit.id} className="relative pl-12">
            <span className="absolute left-2 top-5 h-4 w-4 rounded-full border-4 border-white bg-brand-500 shadow dark:border-surface-950" />
            <Panel>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-brand-500">
                    {visit.type}
                  </p>
                  <h2 className="font-display text-xl font-semibold text-surface-900 dark:text-surface-50">
                    {visit.date}
                  </h2>
                  {visit.source_filename && (
                    <p className="mt-1 text-xs text-surface-500">{visit.source_filename}</p>
                  )}
                </div>
                <span className="rounded-full bg-surface-100 px-3 py-1 text-xs font-medium text-surface-600 dark:bg-surface-800 dark:text-surface-300">
                  {visit.medicines.length} medicines · {visit.labs.length} labs
                </span>
              </div>
              <p className="mt-3 text-sm text-surface-700 dark:text-surface-200">{visit.summary}</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-surface-500">Diagnosis</p>
                  <ul className="mt-1 space-y-1 text-sm">
                    {(visit.diagnosis.length ? visit.diagnosis : ["—"]).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-surface-500">Medicines</p>
                  <ul className="mt-1 space-y-1 text-sm">
                    {(visit.medicines.length
                      ? visit.medicines
                      : [{ name: "None extracted", dosage: "", frequency: "" }]
                    ).map((med) => (
                      <li key={`${visit.id}-${med.name}-${med.dosage}`}>
                        {med.name}
                        {med.dosage ? ` · ${med.dosage}` : ""}
                        {med.frequency ? ` · ${med.frequency}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Panel>
          </article>
        ))}
      </div>
    </div>
  );
}
