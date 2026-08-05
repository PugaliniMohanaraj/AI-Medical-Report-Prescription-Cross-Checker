import { Link } from "react-router-dom";
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import {
  IconChat,
  IconChevron,
  IconLabs,
  IconPill,
  IconShield,
  IconTimeline,
  IconWarning,
} from "@/components/ui/Icons";
import { usePatient } from "@/hooks/usePatient";
import { cn } from "@/utils/cn";

const quickActions = [
  { to: "/timeline", label: "Review timeline", icon: IconTimeline, tone: "bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-100" },
  { to: "/labs", label: "Open lab trends", icon: IconLabs, tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200" },
  { to: "/warnings", label: "Review warnings", icon: IconWarning, tone: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200" },
  { to: "/medicines", label: "Check medicines", icon: IconPill, tone: "bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-200" },
];

export function DashboardPage() {
  const { overview, loading, error, analyzing } = usePatient();
  const visits = overview?.visits ?? [];
  const medicines = overview?.medicines ?? [];
  const findings = overview?.findings ?? [];
  const labs = overview?.lab_trends ?? null;
  const highWarnings = findings.filter((w) => w.severity === "High").length;

  const chartData = useMemo(() => {
    const series = labs?.charts.find((chart) => chart.test_name.toLowerCase().includes("a1c"))
      ?? labs?.charts[0];
    if (!series) return [];
    return series.data.map((point) => ({
      date: point.date.slice(0, 10),
      value: point.value,
      abnormal: point.abnormal,
    }));
  }, [labs]);

  return (
    <div className="space-y-5">
      <MedicalDisclaimer text={overview?.disclaimer} />

      {(error || analyzing || loading) && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3.5 text-base text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          {analyzing
            ? "AI is analyzing uploaded reports…"
            : loading
              ? "Loading patient overview…"
              : error}
        </div>
      )}

      {!overview?.has_extractions && !loading && (
        <div className="rounded-[28px] border border-surface-200 bg-white p-6 dark:border-surface-700 dark:bg-surface-900">
          <h2 className="font-display text-2xl font-semibold">Start with uploads</h2>
          <p className="mt-2 text-base text-surface-600 dark:text-surface-300">
            Upload multi-visit medical reports. The AI will extract medicines, labs, and dates,
            then fill this dashboard, timeline, warnings, and chat.
          </p>
          <Link to="/uploads" className="btn-primary mt-4 inline-flex">
            Upload reports
          </Link>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Visits" value={visits.length} hint="Extracted documents" />
        <KpiCard label="Medicines" value={medicines.length} hint="Across visits" />
        <KpiCard label="Abnormal labs" value={labs?.abnormal_trends.length ?? 0} hint="Trend flags" />
        <KpiCard label="High warnings" value={highWarnings} hint="Prescription safety" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.85fr)]">
        <div className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-[1.4fr_0.9fr]">
            <section className="relative overflow-hidden rounded-[28px] border border-surface-200/80 bg-white p-6 dark:border-surface-700 dark:bg-surface-900">
              <div className="mb-4 flex items-center gap-2">
                <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700 dark:bg-brand-900/40 dark:text-brand-100">
                  Patient snapshot
                </span>
                <span className="text-sm text-surface-500">
                  {[overview?.hospital, overview?.doctor].filter(Boolean).join(" · ") || "From uploaded reports"}
                </span>
              </div>
              <dl className="grid gap-4 sm:grid-cols-2">
                {[
                  ["Name", overview?.patient_name || "Not extracted yet"],
                  ["Patient ID", overview?.patient_id || "—"],
                  ["Allergies", overview?.allergies?.join(", ") || "None listed"],
                  ["Extracted diagnoses", overview?.primary_diagnosis || "—"],
                  ["Latest visit", visits[visits.length - 1]?.date || "—"],
                  ["Documents", String(visits.length)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-surface-400">{label}</dt>
                    <dd className="mt-1.5 text-base font-semibold">{value}</dd>
                  </div>
                ))}
              </dl>
              <Link
                to="/timeline"
                className="mt-5 inline-flex items-center gap-1.5 rounded-2xl bg-brand-500 px-5 py-3 text-base font-semibold text-white"
              >
                View timeline <IconChevron />
              </Link>
            </section>

            <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 dark:border-surface-700 dark:bg-surface-900">
              <h2 className="font-display text-xl font-semibold">Quick actions</h2>
              <div className="mt-4 grid gap-3">
                {quickActions.map((action) => (
                  <Link
                    key={action.to}
                    to={action.to}
                    className="group flex items-center justify-between rounded-2xl border border-surface-100 bg-surface-50/70 px-3.5 py-3.5 transition hover:border-brand-100 hover:bg-white dark:border-surface-700 dark:bg-surface-950/50"
                  >
                    <span className="flex items-center gap-3">
                      <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", action.tone)}>
                        <action.icon className="h-4 w-4" />
                      </span>
                      <span className="text-base font-semibold">{action.label}</span>
                    </span>
                    <IconChevron className="text-surface-400" />
                  </Link>
                ))}
              </div>
            </section>
          </div>

          <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 dark:border-surface-700 dark:bg-surface-900">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="font-display text-xl font-semibold">Lab trend preview</h2>
              <Link to="/labs" className="text-base font-medium text-brand-500 hover:underline">
                Open labs
              </Link>
            </div>
            {chartData.length === 0 ? (
              <p className="text-base text-surface-500">No chartable lab trends yet.</p>
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="#2d6a4f" fill="#2d6a4f33" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
            {labs?.ai_explanation && (
              <p className="mt-3 text-base text-surface-600 dark:text-surface-300">{labs.ai_explanation}</p>
            )}
          </section>
        </div>

        <div className="space-y-5">
          <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 dark:border-surface-700 dark:bg-surface-900">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-xl font-semibold">Safety warnings</h2>
              <Link to="/warnings" className="text-base font-medium text-brand-500 hover:underline">
                View all
              </Link>
            </div>
            {findings.length === 0 ? (
              <p className="text-base text-surface-500">No warnings from extracted medicines.</p>
            ) : (
              <div className="space-y-3">
                {findings.slice(0, 4).map((finding) => (
                  <article
                    key={`${finding.type}-${finding.title}`}
                    className={cn(
                      "rounded-2xl border px-3.5 py-3.5",
                      finding.severity === "High"
                        ? "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30"
                        : "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
                    )}
                  >
                    <p className="text-xs font-semibold uppercase">{finding.severity}</p>
                    <p className="mt-1.5 text-base font-semibold">{finding.title}</p>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 dark:border-surface-700 dark:bg-surface-900">
            <div className="mb-3 flex items-center gap-2">
              <IconShield className="h-4 w-4 text-brand-500" />
              <h2 className="font-display text-xl font-semibold">Ask AI</h2>
            </div>
            <p className="text-base text-surface-600 dark:text-surface-300">
              Follow-up questions use your uploaded reports via RAG, with confidence scores.
            </p>
            <Link to="/chat" className="btn-primary mt-4 inline-flex items-center gap-2">
              <IconChat className="h-4 w-4" /> Open chat
            </Link>
          </section>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string;
  hint: string;
}) {
  return (
    <div className="rounded-[24px] border border-surface-200/80 bg-white p-5 dark:border-surface-700 dark:bg-surface-900">
      <p className="text-sm font-semibold uppercase tracking-wide text-surface-400">{label}</p>
      <p className="mt-2 font-display text-4xl font-semibold">{value}</p>
      <p className="mt-1.5 text-sm text-surface-500">{hint}</p>
    </div>
  );
}
