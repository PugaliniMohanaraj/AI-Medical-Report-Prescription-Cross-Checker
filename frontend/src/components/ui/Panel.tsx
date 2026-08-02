import { cn } from "@/utils/cn";

interface PanelProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Panel({ title, description, actions, children, className }: PanelProps) {
  return (
    <section
      className={cn(
        "rounded-2xl border border-surface-200 bg-white/80 p-5 shadow-sm dark:border-surface-700 dark:bg-surface-900/70",
        className,
      )}
    >
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && (
              <h2 className="font-display text-lg font-semibold text-surface-900 dark:text-surface-50">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">{description}</p>
            )}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
