import { cn } from "@/utils/cn";

interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "danger" | "warning" | "success";
}

const toneStyles = {
  default: "border-surface-200 bg-white/80 dark:border-surface-700 dark:bg-surface-900/80",
  danger: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/40",
  warning: "border-amber-200 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-950/30",
  success: "border-brand-100 bg-brand-50 dark:border-brand-700/40 dark:bg-brand-900/30",
};

export function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
  return (
    <div className={cn("rounded-2xl border px-4 py-4 shadow-sm", toneStyles[tone])}>
      <p className="text-sm font-medium uppercase tracking-wide text-surface-500 dark:text-surface-400">
        {label}
      </p>
      <p className="mt-2 font-display text-4xl font-semibold text-surface-900 dark:text-surface-50">
        {value}
      </p>
      {hint && <p className="mt-1.5 text-sm text-surface-500 dark:text-surface-400">{hint}</p>}
    </div>
  );
}
