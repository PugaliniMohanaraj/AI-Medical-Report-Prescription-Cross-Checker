import { cn } from "@/utils/cn";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-surface-900 dark:text-surface-50">
          {title}
        </h1>
        {description && (
          <p className="max-w-2xl text-sm text-surface-600 dark:text-surface-300">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
