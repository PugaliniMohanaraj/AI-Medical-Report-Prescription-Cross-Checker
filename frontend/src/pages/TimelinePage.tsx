import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { demoVisits } from "@/data/demoPatient";

export function TimelinePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Timeline"
        description="Chronological clinical encounters merged from uploaded reports and structured extraction."
      />

      <div className="relative space-y-4 before:absolute before:bottom-3 before:left-[1.15rem] before:top-3 before:w-px before:bg-brand-200 dark:before:bg-brand-700/50">
        {[...demoVisits].reverse().map((visit) => (
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
                    {visit.diagnosis.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-surface-500">Medicines</p>
                  <ul className="mt-1 space-y-1 text-sm">
                    {visit.medicines.map((med) => (
                      <li key={`${visit.id}-${med.name}`}>
                        {med.name} · {med.dosage} · {med.frequency}
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
