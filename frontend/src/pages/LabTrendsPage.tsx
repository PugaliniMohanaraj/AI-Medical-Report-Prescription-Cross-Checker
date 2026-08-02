import { useEffect, useState } from "react";

import { getErrorMessage } from "@/api/client";
import { analyzeLabTrends } from "@/api/endpoints";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { LabTrendChart } from "@/components/LabTrendChart";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { demoLabVisits, demoPatient } from "@/data/demoPatient";
import type { LabTrendResponse } from "@/types/api";
import { cn } from "@/utils/cn";

export function LabTrendsPage() {
  const [result, setResult] = useState<LabTrendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeLabTrends({
        patient_id: demoPatient.id,
        visits: demoLabVisits,
        include_ai_explanation: true,
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Lab Trends"
        description="Compare markers across visits, highlight abnormal trajectories, and review AI explanations."
        actions={
          <button type="button" className="btn-primary" disabled={loading} onClick={() => void load()}>
            {loading ? "Refreshing…" : "Refresh analysis"}
          </button>
        }
      />

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100">
          {error}
        </div>
      )}

      {result && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <ConfidenceBadge confidence={result.confidence} />
            <span className="text-xs text-surface-500">
              {result.visit_count} visits · {result.series.length} markers · {result.abnormal_trends.length} abnormal
            </span>
          </div>

          {result.ai_explanation && (
            <Panel title="AI explanation">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-surface-700 dark:text-surface-200">
                {result.ai_explanation}
              </p>
            </Panel>
          )}

          {result.abnormal_trends.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2">
              {result.abnormal_trends.map((trend) => (
                <div
                  key={trend.test_name}
                  className={cn(
                    "rounded-2xl border px-4 py-3",
                    trend.severity === "High"
                      ? "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40"
                      : "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold">{trend.test_name}</p>
                    <span className="text-xs font-semibold uppercase">{trend.severity}</span>
                  </div>
                  <p className="mt-1 text-sm">{trend.trend_summary}</p>
                </div>
              ))}
            </div>
          )}

          <div className="grid gap-4 xl:grid-cols-2">
            {result.charts.map((chart) => (
              <LabTrendChart key={chart.test_name} chart={chart} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
