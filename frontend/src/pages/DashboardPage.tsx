import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getErrorMessage } from "@/api/client";
import { analyzeLabTrends, analyzePrescription, queryRag, ingestRagDocuments } from "@/api/endpoints";
import {
  IconChat,
  IconChevron,
  IconLabs,
  IconPill,
  IconShield,
  IconTimeline,
  IconWarning,
} from "@/components/ui/Icons";
import { MiniSparkline } from "@/components/ui/MiniSparkline";
import {
  demoAllergiesText,
  demoLabVisits,
  demoPatient,
  demoVisits,
} from "@/data/demoPatient";
import type { ConflictFinding, LabTrendResponse, RagQueryResponse } from "@/types/api";
import { cn } from "@/utils/cn";

const quickActions = [
  { to: "/timeline", label: "Review timeline", icon: IconTimeline, tone: "bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-100" },
  { to: "/labs", label: "Open lab trends", icon: IconLabs, tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200" },
  { to: "/warnings", label: "Review warnings", icon: IconWarning, tone: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200" },
  { to: "/medicines", label: "Check medicines", icon: IconPill, tone: "bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-200" },
];

export function DashboardPage() {
  const [labs, setLabs] = useState<LabTrendResponse | null>(null);
  const [warnings, setWarnings] = useState<ConflictFinding[]>([]);
  const [chat, setChat] = useState<RagQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const latestMeds = demoVisits[demoVisits.length - 1].medicines;
  const highWarnings = warnings.filter((w) => w.severity === "High").length;

  const hba1cChart = useMemo(() => {
    const series = labs?.charts.find((chart) => chart.test_name.toLowerCase().includes("a1c"));
    if (series) {
      return series.data.map((point) => ({
        date: point.date.slice(5),
        value: point.value,
        abnormal: point.abnormal,
      }));
    }
    return demoVisits.map((visit) => {
      const hba1c = visit.labs.find((lab) => lab.test_name.toLowerCase().includes("a1c"));
      return {
        date: visit.date.slice(5),
        value: Number(hba1c?.value ?? 0),
        abnormal: Number(hba1c?.value ?? 0) > 5.6,
      };
    });
  }, [labs]);

  useEffect(() => {
    void (async () => {
      try {
        const [labResult, rxResult] = await Promise.all([
          analyzeLabTrends({
            patient_id: demoPatient.id,
            visits: demoLabVisits,
            include_ai_explanation: true,
          }),
          analyzePrescription({
            medicines: latestMeds.map((m) => ({ ...m })),
            allergies: demoPatient.allergies,
          }),
        ]);
        setLabs(labResult);
        setWarnings(rxResult.findings.slice(0, 4));

        try {
          await ingestRagDocuments({
            patient_id: demoPatient.id,
            documents: [
              {
                document_id: "dash-note",
                title: "Allergy Information - Dr. Note",
                content: `Patient ${demoPatient.name}. Allergy: ${demoAllergiesText}. Diagnosis: ${demoPatient.primaryDiagnosis}. Latest HbA1c trending upward across visits.`,
                source: "dashboard",
              },
            ],
          });
          const answer = await queryRag({
            question: "Did any medicine conflict?",
            patient_id: demoPatient.id,
            top_k: 3,
          });
          setChat(answer);
        } catch {
          // Chat preview is optional on the dashboard.
        }
      } catch (err) {
        setError(getErrorMessage(err));
      }
    })();
  }, [latestMeds]);

  return (
    <div className="space-y-5">
      {error && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          Live API unavailable ({error}). Demo dashboard remains interactive.
        </div>
      )}

      {/* KPI row */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Visits"
          value={demoVisits.length}
          hint="Across timeline"
          spark={[1, 1, 2, 2, 3]}
          sparkColor="#2d6a4f"
          iconTone="bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-100"
        />
        <KpiCard
          label="Active medicines"
          value={latestMeds.length}
          hint="Latest encounter"
          spark={[2, 2, 3, 4, 5]}
          sparkColor="#059669"
          iconTone="bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-200"
        />
        <KpiCard
          label="Abnormal labs"
          value={labs?.abnormal_trends.length ?? "—"}
          hint="Cross-visit markers"
          spark={[1, 1, 2, 2, 3]}
          sparkColor="#d97706"
          iconTone="bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-200"
        />
        <KpiCard
          label="High warnings"
          value={highWarnings || warnings.length || "—"}
          hint="Prescription safety"
          spark={[0, 1, 1, 2, highWarnings || 2]}
          sparkColor="#dc2626"
          iconTone="bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-200"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.85fr)]">
        <div className="space-y-5">
          {/* Patient + quick actions */}
          <div className="grid gap-5 lg:grid-cols-[1.4fr_0.9fr]">
            <section className="relative overflow-hidden rounded-[28px] border border-surface-200/80 bg-white p-6 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900">
              <div className="absolute -right-8 -top-10 h-40 w-40 rounded-full bg-brand-500/10 blur-2xl" />
              <div className="relative flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="mb-4 flex items-center gap-2">
                    <span className="rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-brand-700 dark:bg-brand-900/40 dark:text-brand-100">
                      Patient snapshot
                    </span>
                    <span className="text-xs text-surface-500">
                      {demoPatient.hospital} · {demoPatient.physician}
                    </span>
                  </div>
                  <dl className="grid gap-4 sm:grid-cols-2">
                    {[
                      ["Name", demoPatient.name],
                      ["MRN", demoPatient.mrn],
                      ["Age / Sex", `${demoPatient.age} / ${demoPatient.sex}`],
                      ["Allergies", demoAllergiesText],
                      ["Primary diagnosis", demoPatient.primaryDiagnosis],
                      ["Latest visit", demoVisits[demoVisits.length - 1].date],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <dt className="text-[11px] font-semibold uppercase tracking-wide text-surface-400">
                          {label}
                        </dt>
                        <dd className="mt-1 text-sm font-semibold text-surface-900 dark:text-surface-50">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <Link
                    to="/timeline"
                    className="mt-5 inline-flex items-center gap-1 rounded-2xl bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-brand-500/20 transition hover:bg-brand-700"
                  >
                    View full profile <IconChevron />
                  </Link>
                </div>
                <div className="mx-auto flex h-36 w-36 shrink-0 items-center justify-center rounded-[28px] bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/50 dark:to-surface-800">
                  <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-white shadow-xl dark:bg-surface-900">
                    <IconShield className="h-10 w-10 text-brand-500" />
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900">
              <h2 className="font-display text-lg font-semibold">Quick actions</h2>
              <div className="mt-4 grid gap-3">
                {quickActions.map((action) => (
                  <Link
                    key={action.to}
                    to={action.to}
                    className="group flex items-center justify-between rounded-2xl border border-surface-100 bg-surface-50/70 px-3 py-3 transition hover:-translate-y-0.5 hover:border-brand-100 hover:bg-white hover:shadow-md dark:border-surface-700 dark:bg-surface-950/50 dark:hover:border-brand-700/40 dark:hover:bg-surface-800"
                  >
                    <span className="flex items-center gap-3">
                      <span className={cn("flex h-10 w-10 items-center justify-center rounded-2xl", action.tone)}>
                        <action.icon className="h-5 w-5" />
                      </span>
                      <span className="text-sm font-semibold">{action.label}</span>
                    </span>
                    <IconChevron className="text-surface-400 transition group-hover:text-brand-500" />
                  </Link>
                ))}
              </div>
              <p className="mt-4 rounded-2xl bg-brand-50 px-3 py-2 text-xs text-brand-700 dark:bg-brand-900/30 dark:text-brand-100">
                Demo regimen ready · {latestMeds.length} active medicines loaded
              </p>
            </section>
          </div>

          {/* Warnings + labs */}
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h2 className="font-display text-lg font-semibold">Recent safety warnings</h2>
                <Link to="/warnings" className="text-sm font-medium text-brand-500 hover:underline">
                  View all
                </Link>
              </div>
              {warnings.length === 0 ? (
                <p className="text-sm text-surface-500">No warnings loaded yet.</p>
              ) : (
                <ul className="space-y-3">
                  {warnings.map((warning) => (
                    <li
                      key={`${warning.type}-${warning.title}`}
                      className="flex items-start gap-3 rounded-2xl border border-surface-100 bg-surface-50/80 px-3 py-3 dark:border-surface-700 dark:bg-surface-950/40"
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
                          warning.severity === "High"
                            ? "bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-300"
                            : "bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-200",
                        )}
                      >
                        <IconWarning className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-sm font-semibold">{warning.title}</p>
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                              warning.severity === "High"
                                ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-200"
                                : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-200",
                            )}
                          >
                            {warning.severity}
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-surface-500">
                          {warning.explanation}
                        </p>
                      </div>
                      <IconChevron className="mt-2 shrink-0 text-surface-300" />
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div>
                  <h2 className="font-display text-lg font-semibold">Lab trends</h2>
                  <p className="text-xs text-surface-500">HbA1c % across visits</p>
                </div>
                <Link to="/labs" className="text-sm font-medium text-brand-500 hover:underline">
                  Details
                </Link>
              </div>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={hba1cChart} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
                    <defs>
                      <linearGradient id="hba1cFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2d6a4f" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#2d6a4f" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#d9e5de" strokeOpacity={0.7} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#879e92" }} axisLine={false} tickLine={false} />
                    <YAxis domain={[5, 9]} tick={{ fontSize: 11, fill: "#879e92" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 14,
                        borderColor: "#dceee6",
                        fontSize: 12,
                      }}
                    />
                    <ReferenceLine y={5.6} stroke="#16a34a" strokeDasharray="4 4" label={{ value: "Normal", fill: "#16a34a", fontSize: 10 }} />
                    <ReferenceLine y={7.5} stroke="#dc2626" strokeDasharray="4 4" label={{ value: "High", fill: "#dc2626", fontSize: 10 }} />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#2d6a4f"
                      strokeWidth={3}
                      fill="url(#hba1cFill)"
                      dot={{ r: 4, fill: "#2d6a4f", stroke: "#fff", strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <Link
                to="/chat"
                className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-brand-100 bg-brand-50 px-3 py-2.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-100 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-100"
              >
                <IconChat className="h-4 w-4" /> Ask AI about this
              </Link>
            </section>
          </div>

          {/* AI summary + medicines */}
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-[28px] border border-surface-200/80 bg-gradient-to-br from-white to-brand-50/40 p-5 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:from-surface-900 dark:to-brand-950/20">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">AI lab summary</h2>
                <Link to="/labs" className="text-sm font-medium text-brand-500 hover:underline">
                  Details
                </Link>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-surface-700 dark:text-surface-200">
                {labs?.ai_explanation ||
                  "HbA1c is rising across visits and remains above the reference range, suggesting worsening glycemic control. Correlate with adherence and follow-up labs."}
              </p>
            </section>

            <section className="rounded-[28px] border border-surface-200/80 bg-white p-5 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">Active medicines</h2>
                <Link to="/medicines" className="text-sm font-medium text-brand-500 hover:underline">
                  Manage
                </Link>
              </div>
              <ul className="space-y-2.5">
                {latestMeds.slice(0, 5).map((med) => (
                  <li
                    key={med.name}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-surface-100 px-3 py-2.5 dark:border-surface-700"
                  >
                    <span className="flex min-w-0 items-center gap-3">
                      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-100">
                        <IconPill className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <p className="truncate text-sm font-semibold">{med.name}</p>
                        <p className="truncate text-xs text-surface-500">
                          {med.dosage} · {med.frequency}
                        </p>
                      </span>
                    </span>
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-200">
                      Active
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>

        {/* AI Assistant column */}
        <aside className="rounded-[28px] border border-surface-200/80 bg-white p-5 shadow-[0_18px_50px_-32px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900 xl:sticky xl:top-28 xl:self-start">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg font-semibold">AI Assistant</h2>
              <p className="text-xs text-surface-500">Follow-up answers with citations</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Online
            </span>
          </div>

          <div className="space-y-3">
            <div className="ml-8 rounded-2xl rounded-tr-md bg-brand-500 px-3.5 py-2.5 text-sm text-white shadow-md shadow-brand-500/20">
              Did any medicine conflict?
            </div>
            <div className="mr-4 rounded-2xl rounded-tl-md border border-surface-100 bg-surface-50 px-3.5 py-3 text-sm leading-relaxed text-surface-700 dark:border-surface-700 dark:bg-surface-950/50 dark:text-surface-200">
              {chat?.answer ||
                "Yes. Supporting documents report a high-severity Warfarin + Aspirin interaction and an Amoxicillin allergy conflict with Penicillin."}
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-medium text-surface-500">Confidence</span>
              <span className="font-semibold text-brand-600 dark:text-brand-100">
                {Math.round((chat?.confidence.score ?? 0.86) * 100)}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-100 dark:bg-surface-800">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-emerald-400"
                style={{ width: `${Math.round((chat?.confidence.score ?? 0.86) * 100)}%` }}
              />
            </div>
          </div>

          <div className="mt-5">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-surface-400">Sources</p>
            <ul className="space-y-2">
              {(chat?.sources.length
                ? chat.sources.slice(0, 3)
                : [
                    {
                      document_id: "Allergy Information - Dr. Note",
                      excerpt: "Penicillin allergy documented; avoid beta-lactams.",
                      title: "Allergy Information - Dr. Note",
                    },
                  ]
              ).map((source) => (
                <li
                  key={`${source.document_id}-${source.excerpt.slice(0, 18)}`}
                  className="rounded-2xl border border-surface-100 bg-surface-50/80 px-3 py-2.5 dark:border-surface-700 dark:bg-surface-950/40"
                >
                  <p className="text-xs font-semibold">{source.title || source.document_id}</p>
                  <p className="mt-1 line-clamp-2 text-[11px] text-surface-500">{source.excerpt}</p>
                </li>
              ))}
            </ul>
          </div>

          <Link
            to="/chat"
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-brand-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-700"
          >
            Open full AI chat
          </Link>
        </aside>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
  spark,
  sparkColor,
  iconTone,
}: {
  label: string;
  value: string | number;
  hint: string;
  spark: number[];
  sparkColor: string;
  iconTone: string;
}) {
  return (
    <div className="rounded-[24px] border border-surface-200/80 bg-white p-4 shadow-[0_16px_40px_-28px_rgba(15,31,25,0.45)] dark:border-surface-700 dark:bg-surface-900">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-surface-400">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold tracking-tight">{value}</p>
          <p className="mt-1 text-xs text-surface-500">{hint}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className={cn("flex h-9 w-9 items-center justify-center rounded-2xl", iconTone)}>
            <span className="h-2 w-2 rounded-full bg-current opacity-80" />
          </span>
          <MiniSparkline values={spark} stroke={sparkColor} />
        </div>
      </div>
    </div>
  );
}
