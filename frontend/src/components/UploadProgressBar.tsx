interface UploadProgressBarProps {
  progress: number;
  label?: string;
}

export function UploadProgressBar({ progress, label }: UploadProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(progress)));

  return (
    <div className="space-y-2" aria-live="polite">
      <div className="flex items-center justify-between text-sm text-brand-700">
        <span>{label ?? "Uploading…"}</span>
        <span className="tabular-nums">{clamped}%</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-brand-100">
        <div
          className="h-full rounded-full bg-brand-500 transition-[width] duration-200 ease-out"
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
