import { useMemo, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { IconBell, IconMenu, IconSearch } from "@/components/ui/Icons";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { demoPatient } from "@/data/demoPatient";
import { cn } from "@/utils/cn";

function greetingForNow() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const pageCaptions: Record<string, string> = {
  "/dashboard": "Here's today's clinical overview for your patient.",
  "/timeline": "Browse visits in chronological order.",
  "/medicines": "Review regimen details and safety checks.",
  "/labs": "Track markers and abnormal trends over time.",
  "/warnings": "Prioritized prescription and allergy alerts.",
  "/chat": "Ask follow-up questions with cited sources.",
  "/settings": "Appearance, API status, and workspace preferences.",
  "/uploads": "Ingest multi-PDF medical reports securely.",
};

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { health } = useHealthCheck();
  const location = useLocation();
  const firstName = demoPatient.name.split(" ")[0];
  const caption = useMemo(
    () => pageCaptions[location.pathname] ?? "Clinical report & prescription cross-checker.",
    [location.pathname],
  );

  return (
    <div className="min-h-screen bg-[#f4f7f5] text-surface-900 dark:bg-surface-950 dark:text-surface-50">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_right,rgba(45,106,79,0.08),transparent_28%)] dark:bg-[radial-gradient(circle_at_top_right,rgba(45,106,79,0.16),transparent_30%)]" />

      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside className="sticky top-0 hidden h-screen w-[272px] shrink-0 overflow-hidden rounded-none lg:block">
          <Sidebar />
        </aside>

        {mobileOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <button
              type="button"
              className="absolute inset-0 bg-black/45"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
            />
            <aside className="absolute inset-y-0 left-0 w-[280px] overflow-hidden shadow-2xl">
              <Sidebar onNavigate={() => setMobileOpen(false)} />
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-surface-200/70 bg-[#f4f7f5]/85 backdrop-blur-xl dark:border-surface-800 dark:bg-surface-950/80">
            <div className="flex flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <button
                    type="button"
                    className="rounded-xl border border-surface-200 bg-white p-2 text-surface-700 shadow-sm dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200 lg:hidden"
                    onClick={() => setMobileOpen(true)}
                    aria-label="Open navigation"
                  >
                    <IconMenu />
                  </button>
                  <div className="min-w-0">
                    <h1 className="truncate font-display text-2xl font-semibold tracking-tight text-surface-900 dark:text-surface-50">
                      {greetingForNow()}, {firstName}!
                    </h1>
                    <p className="truncate text-sm text-surface-500 dark:text-surface-400">{caption}</p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to="/uploads"
                    className="rounded-2xl bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-700"
                  >
                    Upload reports
                  </Link>
                  <Link
                    to="/chat"
                    className="rounded-2xl border border-brand-100 bg-brand-50 px-4 py-2.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-100 dark:border-brand-700/40 dark:bg-brand-900/40 dark:text-brand-100"
                  >
                    Ask AI
                  </Link>
                  <button
                    type="button"
                    className="relative rounded-2xl border border-surface-200 bg-white p-2.5 text-surface-600 shadow-sm dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200"
                    aria-label="Notifications"
                  >
                    <IconBell />
                    <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
                  </button>
                  <div className="flex items-center gap-2 rounded-2xl border border-surface-200 bg-white py-1.5 pl-1.5 pr-3 shadow-sm dark:border-surface-700 dark:bg-surface-900">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500 text-sm font-semibold text-white">
                      {firstName.slice(0, 1)}
                    </div>
                    <div className="hidden sm:block">
                      <p className="text-xs font-semibold leading-tight">{demoPatient.name}</p>
                      <p className="text-[10px] text-surface-500">{demoPatient.mrn}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="relative max-w-2xl">
                <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
                <input
                  className="w-full rounded-2xl border border-surface-200 bg-white py-2.5 pl-10 pr-16 text-sm shadow-sm outline-none ring-brand-500 placeholder:text-surface-400 focus:ring-2 dark:border-surface-700 dark:bg-surface-900"
                  placeholder="Search visits, medicines, labs, warnings…"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-surface-200 px-1.5 py-0.5 text-[10px] font-medium text-surface-400 dark:border-surface-700">
                  ⌘K
                </span>
              </div>

              <div className="flex items-center gap-2 text-[11px]">
                <span
                  className={cn(
                    "inline-flex rounded-full px-2.5 py-1 font-medium",
                    health?.status === "ok"
                      ? "bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-100"
                      : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
                  )}
                >
                  API {health?.status === "ok" ? "online" : "checking"}
                  {health?.llm_provider ? ` · ${health.llm_provider}` : ""}
                </span>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
