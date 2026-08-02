import { Link, NavLink } from "react-router-dom";
import type { ReactNode } from "react";

import {
  IconChat,
  IconDashboard,
  IconLabs,
  IconMoon,
  IconPill,
  IconSettings,
  IconShield,
  IconSun,
  IconTimeline,
  IconUpload,
  IconWarning,
} from "@/components/ui/Icons";
import { useTheme } from "@/theme/ThemeProvider";
import { cn } from "@/utils/cn";

const primaryNav = [
  { to: "/dashboard", label: "Dashboard", icon: IconDashboard },
  { to: "/timeline", label: "Timeline", icon: IconTimeline },
  { to: "/medicines", label: "Medicines", icon: IconPill },
  { to: "/labs", label: "Lab Trends", icon: IconLabs },
  { to: "/warnings", label: "Warnings", icon: IconWarning },
  { to: "/chat", label: "AI Chat", icon: IconChat },
];

const secondaryNav = [
  { to: "/uploads", label: "Uploads", icon: IconUpload },
  { to: "/settings", label: "Settings", icon: IconSettings },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-full flex-col bg-[#0f1f19] text-white">
      <div className="px-5 pb-2 pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-500 shadow-lg shadow-brand-500/30">
            <IconShield className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-display text-xl font-semibold tracking-tight">MedCross</p>
            <p className="text-[11px] text-white/55">Clinical intelligence</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        <div className="space-y-1">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35">
            Clinical
          </p>
          {primaryNav.map((item) => (
            <SideLink key={item.to} {...item} onNavigate={onNavigate} />
          ))}
        </div>
        <div className="space-y-1">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35">
            System
          </p>
          {secondaryNav.map((item) => (
            <SideLink key={item.to} {...item} onNavigate={onNavigate} />
          ))}
        </div>
      </nav>

      <div className="space-y-3 px-4 pb-5">
        <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-brand-500/25 to-brand-700/10 p-4">
          <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500/30">
            <IconShield className="h-4 w-4 text-brand-100" />
          </div>
          <p className="text-sm font-semibold">Your health, our priority</p>
          <p className="mt-1 text-xs leading-relaxed text-white/60">
            Cross-check reports, medicines, and labs with confidence.
          </p>
          <Link
            to="/chat"
            onClick={onNavigate}
            className="mt-3 inline-flex rounded-xl bg-brand-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-brand-700"
          >
            Learn more
          </Link>
        </div>

        <button
          type="button"
          onClick={toggleTheme}
          className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-xs font-medium text-white/80 transition hover:bg-white/10"
        >
          <span>{theme === "dark" ? "Dark mode" : "Light mode"}</span>
          {theme === "dark" ? <IconSun className="h-4 w-4" /> : <IconMoon className="h-4 w-4" />}
        </button>
        <p className="px-1 text-[10px] text-white/35">© {new Date().getFullYear()} MedCross</p>
      </div>
    </div>
  );
}

function SideLink({
  to,
  label,
  icon: Icon,
  onNavigate,
}: {
  to: string;
  label: string;
  icon: (props: { className?: string }) => ReactNode;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-all",
          isActive
            ? "bg-brand-500 text-white shadow-lg shadow-brand-500/25"
            : "text-white/65 hover:bg-white/8 hover:text-white",
        )
      }
    >
      <Icon className="shrink-0 opacity-90" />
      <span>{label}</span>
    </NavLink>
  );
}
