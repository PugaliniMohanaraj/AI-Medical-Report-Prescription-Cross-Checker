import { Link } from "react-router-dom";

import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { useTheme } from "@/theme/ThemeProvider";

export function SettingsPage() {
  const { theme, setTheme, toggleTheme } = useTheme();
  const { health, loading, refresh, error } = useHealthCheck();
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Appearance, API connectivity, and workspace preferences."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Appearance">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">Dark mode</p>
              <p className="text-xs text-surface-500">Currently {theme}</p>
            </div>
            <button type="button" className="btn-secondary" onClick={toggleTheme}>
              Switch to {theme === "dark" ? "light" : "dark"}
            </button>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className={`btn-secondary flex-1 ${theme === "light" ? "ring-2 ring-brand-500" : ""}`}
              onClick={() => setTheme("light")}
            >
              Light
            </button>
            <button
              type="button"
              className={`btn-secondary flex-1 ${theme === "dark" ? "ring-2 ring-brand-500" : ""}`}
              onClick={() => setTheme("dark")}
            >
              Dark
            </button>
          </div>
        </Panel>

        <Panel
          title="API status"
          actions={
            <button type="button" className="btn-secondary" disabled={loading} onClick={() => void refresh()}>
              Refresh
            </button>
          }
        >
          {error && <p className="mb-2 text-sm text-red-600 dark:text-red-300">{error}</p>}
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-surface-500">Base URL</dt>
              <dd className="font-mono text-xs">{apiBase}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-surface-500">Status</dt>
              <dd>{health?.status ?? (loading ? "checking…" : "unknown")}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-surface-500">Environment</dt>
              <dd>{health?.environment ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-surface-500">LLM provider</dt>
              <dd>{health?.llm_provider ?? "—"}</dd>
            </div>
          </dl>
        </Panel>

        <Panel title="Workspace" description="Document intake and model switching">
          <div className="space-y-3 text-sm">
            <p>
              Upload multi-PDF reports from the{" "}
              <Link className="font-medium text-brand-500 underline-offset-2 hover:underline" to="/uploads">
                Uploads
              </Link>{" "}
              page.
            </p>
            <p className="text-surface-600 dark:text-surface-300">
              Switch backend LLM with <code className="rounded bg-surface-100 px-1 dark:bg-surface-800">LLM_PROVIDER=ollama|openai</code> in{" "}
              <code className="rounded bg-surface-100 px-1 dark:bg-surface-800">backend/.env</code>.
            </p>
          </div>
        </Panel>

        <Panel title="About MedCross">
          <p className="text-sm leading-relaxed text-surface-700 dark:text-surface-200">
            AI Medical Report & Prescription Cross-Checker for competition demos — PDF intake,
            structured extraction, prescription safety, lab trends, and RAG follow-up chat.
          </p>
        </Panel>
      </div>
    </div>
  );
}
