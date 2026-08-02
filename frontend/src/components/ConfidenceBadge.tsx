import type { ConfidenceScore } from "@/types/api";

interface ConfidenceBadgeProps {
  confidence?: ConfidenceScore | null;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (!confidence) {
    return (
      <span className="inline-flex items-center rounded-md bg-brand-100 px-2 py-1 text-xs text-brand-700 dark:bg-brand-900/50 dark:text-brand-100">
        Confidence pending
      </span>
    );
  }

  const pct = Math.round(confidence.score * 100);

  return (
    <span
      className="inline-flex items-center rounded-md bg-brand-100 px-2 py-1 text-xs font-medium text-brand-700 dark:bg-brand-900/50 dark:text-brand-100"
      title={confidence.rationale ?? undefined}
    >
      Confidence {pct}%
    </span>
  );
}
