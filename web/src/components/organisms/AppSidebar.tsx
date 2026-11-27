import { useState } from "react";
import { NavLink } from "react-router-dom";
import { ExternalLink, FlaskConical, KeyRound, LayoutDashboard, PanelLeftClose, PanelLeftOpen, UploadCloud, type LucideIcon } from "lucide-react";
import { useActiveRanking, useHealth } from "@/api/hooks";
import { BrandLogo, Pennant, SilverRule, StatusDot } from "@/components/atoms";
import { bandStyle } from "@/lib/domain";
import { cn } from "@/lib/utils";
import { useApiKeyDialog } from "@/providers/ApiKeyProvider";

const monitors = [
  {
    href: "https://smith.langchain.com/o/7a4526a7-3b9f-47d7-9d9e-dfd7d0bc72ce/projects/p/de709903-804e-416e-99f5-a2bc94803de5",
    label: "LangSmith",
    hint: "Chat traces",
    external: true,
  },
  {
    href: "/mlflow/#/experiments/1",
    label: "MLflow",
    hint: "Model versions",
    external: true,
  },
  {
    href: "/docs",
    label: "Swagger",
    hint: "API endpoints",
    external: false,
  },
];

const SIDEBAR_KEY = "esm.shiprisk.sidebarCollapsed";

const nav: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/fleet", label: "Fleet risk", icon: LayoutDashboard, end: true },
  { to: "/upload", label: "Data upload", icon: UploadCloud },
  { to: "/validation", label: "Validation", icon: FlaskConical },
];

export function ObservabilityLinks({
  tone = "dark",
  onNavigate,
  compact = false,
}: {
  tone?: "dark" | "light";
  onNavigate?: () => void;
  compact?: boolean;
}) {
  const dark = tone === "dark";
  return (
    <div className={cn("space-y-2", compact ? "px-2" : "px-3")}>
      {compact ? null : <p className={cn("text-eyebrow px-2", dark ? "text-white/45" : "text-muted-foreground")}>Observability</p>}
      <ul className="space-y-0.5">
        {monitors.map((item) => (
          <li key={item.label}>
            <a
              href={item.href}
              title={`${item.label} · ${item.hint}`}
              target={item.external ? "_blank" : undefined}
              rel={item.external ? "noreferrer" : undefined}
              onClick={(event) => {
                onNavigate?.();
                if (!item.external) {
                  event.preventDefault();
                  window.location.assign(item.href);
                }
              }}
              className={cn(
                "flex items-center rounded-md text-[13px] transition-colors",
                compact ? "justify-center px-2 py-2" : "gap-2.5 px-2 py-1.5",
                dark ? "text-white/75 hover:bg-white/[0.07] hover:text-white" : "text-navy-800 hover:bg-navy-50",
              )}
            >
              <ExternalLink className="size-3.5 shrink-0" />
              {compact ? <span className="sr-only">{item.label}</span> : <span className="flex-1 truncate">{item.label}</span>}
              {compact ? null : <span className={cn("text-[11px]", dark ? "text-white/40" : "text-muted-foreground")}>{item.hint}</span>}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Watchlist() {
  const { data } = useActiveRanking();
  const high = (data ?? []).filter((r) => r.band === "High");
  if (!high.length) return null;
  return (
    <div className="space-y-2 px-3 pb-3">
      <p className="text-eyebrow sticky top-0 z-10 bg-navy-900 px-2 py-1 text-white/45">Watchlist · {high.length}</p>
      <ul className="space-y-0.5">
        {high.map((v) => (
          <li key={v.vessel_id}>
            <NavLink
              to={`/vessels/${v.vessel_id}`}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] text-white/75 transition-colors hover:bg-white/[0.07] hover:text-white",
                  isActive && "bg-white/10 text-white",
                )
              }
            >
              <Pennant className="size-3" color={bandStyle.High.hex} />
              <span className="flex-1 truncate">{v.vessel_name ?? v.vessel_id}</span>
              <span className="font-heading text-xs font-semibold tabular text-white/60">{v.score.toFixed(0)}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SystemStatus({ compact = false }: { compact?: boolean }) {
  const { data, isError } = useHealth();
  const tone = (s?: string): "ok" | "bad" | "idle" => (s === "up" ? "ok" : s === "down" ? "bad" : "idle");
  const rows = [
    { label: "Risk API", tone: isError ? "bad" : data ? "ok" : "idle", pulse: !!data && !isError },
    { label: "PostgreSQL", tone: tone(data?.postgres), pulse: false },
    { label: "Qdrant evidence", tone: tone(data?.qdrant), pulse: false },
  ] as const;
  if (compact) {
    return (
      <div className="flex flex-col items-center gap-2 py-1">
        {rows.map((row) => (
          <span key={row.label} title={row.label} className="inline-flex">
            <StatusDot tone={row.tone} pulse={row.pulse} />
          </span>
        ))}
      </div>
    );
  }
  return (
    <div className="space-y-1.5 rounded-lg bg-white/[0.04] px-3 py-2.5 text-[12px] text-white/70">
      {rows.map((row) => (
        <div key={row.label} className="flex items-center justify-between">
          <span>{row.label}</span>
          <StatusDot tone={row.tone} pulse={row.pulse} />
        </div>
      ))}
    </div>
  );
}

function useCollapsed() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_KEY) === "1");
  const toggle = () => {
    setCollapsed((value) => {
      const next = !value;
      localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      return next;
    });
  };
  return { collapsed, toggle };
}

export function AppSidebar() {
  const { open, user } = useApiKeyDialog();
  const { collapsed, toggle } = useCollapsed();
  const initial = (user || "?").slice(0, 1).toUpperCase();
  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-white/10 bg-bridge text-sidebar-foreground transition-[width] duration-200 ease-out lg:flex",
        collapsed ? "w-[4.5rem]" : "w-64",
      )}
    >
      <div className={cn("bg-white", collapsed ? "flex justify-center px-2 py-4" : "px-5 pt-5 pb-4")}>
        <BrandLogo variant={collapsed ? "mark" : "full"} size="sm" />
        {collapsed ? null : (
          <p className="mt-3 font-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-navy-700">
            Detention Early Warning
          </p>
        )}
      </div>
      <SilverRule className="h-1 rounded-none" />

      <nav className="space-y-0.5 px-2 pt-4">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={label}
            className={({ isActive }) =>
              cn(
                "relative flex items-center gap-3 rounded-md py-2 text-sm font-medium text-white/70 transition-colors hover:bg-white/[0.07] hover:text-white",
                collapsed ? "justify-center px-2" : "px-3",
                isActive && "bg-white/10 text-white before:absolute before:inset-y-1.5 before:-left-2 before:w-1 before:rounded-r before:bg-silver",
              )
            }
          >
            <Icon className="size-4 shrink-0" />
            {collapsed ? <span className="sr-only">{label}</span> : label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-4">
        <ObservabilityLinks compact={collapsed} />
      </div>

      {collapsed ? (
        <div className="min-h-0 flex-1" />
      ) : (
        <div className="sidebar-scroll mt-4 min-h-0 flex-1 overflow-x-hidden overflow-y-auto">
          <Watchlist />
        </div>
      )}

      <div className={cn("space-y-3 border-t border-white/[0.08]", collapsed ? "px-2 py-3" : "p-3")}>
        <SystemStatus compact={collapsed} />
        <button
          type="button"
          onClick={open}
          title={user || "Set operator"}
          className={cn(
            "flex w-full items-center rounded-md py-2 text-left text-[13px] text-white/70 transition-colors hover:bg-white/[0.07] hover:text-white",
            collapsed ? "justify-center px-1" : "gap-2.5 px-2",
          )}
        >
          <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-white/10 font-heading text-xs font-bold text-white">
            {initial}
          </span>
          {collapsed ? <span className="sr-only">{user || "Set operator"}</span> : <span className="flex-1 truncate">{user || "Set operator"}</span>}
          {collapsed ? null : <KeyRound className="size-3.5" />}
        </button>
      </div>

      <button
        type="button"
        onClick={toggle}
        aria-expanded={!collapsed}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="absolute top-16 -right-3 z-40 flex size-6 items-center justify-center rounded-full border border-white/20 bg-navy-800 text-white shadow-sm transition-colors hover:bg-navy-700"
      >
        {collapsed ? <PanelLeftOpen className="size-3.5" /> : <PanelLeftClose className="size-3.5" />}
      </button>
    </aside>
  );
}
