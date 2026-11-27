import { useState } from "react";
import { NavLink, useMatches } from "react-router-dom";
import { CalendarDays, FlaskConical, LayoutDashboard, Menu, UploadCloud } from "lucide-react";
import { useRanking } from "@/api/hooks";
import { BrandLogo, SilverRule } from "@/components/atoms";
import { ObservabilityLinks } from "@/components/organisms/AppSidebar";
import { useScoringMode } from "@/providers/ScoringModeProvider";
import type { ScoringMode } from "@/lib/scoringMode";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { formatDate } from "@/lib/domain";
import { cn } from "@/lib/utils";

const mobileNav = [
  { to: "/", label: "Fleet risk", icon: LayoutDashboard, end: true },
  { to: "/upload", label: "Data upload", icon: UploadCloud },
  { to: "/validation", label: "Validation", icon: FlaskConical },
];

function ScoringToggle() {
  const { mode, setMode } = useScoringMode();
  const options: { id: ScoringMode; label: string }[] = [
    { id: "rules", label: "Rules" },
    { id: "model", label: "Model" },
  ];
  return (
    <div role="group" aria-label="Scoring approach" className="inline-flex rounded-md border bg-card p-0.5">
      {options.map((option) => {
        const active = mode === option.id;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => setMode(option.id)}
            className={cn(
              "rounded px-2.5 py-1 text-xs font-medium",
              active ? "bg-navy-900 text-white" : "text-muted-foreground hover:text-navy-900",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function TopBar() {
  const { data } = useRanking();
  const [open, setOpen] = useState(false);
  const matches = useMatches();
  const crumb = [...matches].reverse().find((m) => (m.handle as { crumb?: string } | undefined)?.crumb);
  const asOf = data?.[0]?.as_of;

  return (
    <div className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="flex h-14 items-center gap-3 px-4 md:px-8">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
              <Menu className="size-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0">
            <SheetHeader className="p-5">
              <SheetTitle>
                <BrandLogo size="sm" />
              </SheetTitle>
            </SheetHeader>
            <SilverRule className="rounded-none" />
            <nav className="space-y-1 p-3">
              {mobileNav.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium", isActive ? "bg-navy-50 text-navy-800" : "text-muted-foreground")
                  }
                >
                  <Icon className="size-4" /> {label}
                </NavLink>
              ))}
            </nav>
            <ObservabilityLinks tone="light" onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>

        <div className="flex min-w-0 items-center gap-2 text-sm">
          <span className="hidden text-muted-foreground sm:inline">ESM Fleet</span>
          <span className="hidden text-silver-400 sm:inline">/</span>
          <span className="truncate font-medium text-navy-900">{crumb ? (crumb.handle as { crumb: string }).crumb : ""}</span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <ScoringToggle />
          {asOf && (
            <span className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2.5 py-1 text-xs text-muted-foreground">
              <CalendarDays className="size-3.5" />
              Scored as of <span className="font-medium text-foreground">{formatDate(asOf)}</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
