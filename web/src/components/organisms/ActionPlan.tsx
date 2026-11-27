import { useState } from "react";
import { CheckCheck, ClipboardList, Hourglass, Users } from "lucide-react";
import type { VesselAction, VesselRisk } from "@/api/types";
import { DueDate, OwnerTag } from "@/components/atoms";
import { EmptyState, RecordIdList, SectionCard } from "@/components/molecules";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { daysBetween, formatDate } from "@/lib/domain";
import { cn } from "@/lib/utils";
import { CompleteActionDialog } from "./CompleteActionDialog";

const OWNERS = ["Marine", "Technical", "Crewing", "HSQE"] as const;

interface ActionPlanProps {
  risk: VesselRisk;
  actions?: VesselAction[];
  loading?: boolean;
}

function ActionList({ open, asOf, onComplete }: { open: VesselAction[]; asOf: string; onComplete: (a: VesselAction) => void }) {
  if (!open.length) {
    return <EmptyState icon={CheckCheck} title="No open actions" description="Nothing in the current data triggers an action rule for this vessel." />;
  }
  return (
    <ol className="space-y-3">
      {open.map((a, i) => (
        <li key={a.id} className="group flex gap-4 rounded-lg border bg-card p-4 transition-shadow hover:shadow-md hover:shadow-navy-900/5">
          <span className="font-display text-xl font-bold leading-none text-silver-400 tabular">{String(i + 1).padStart(2, "0")}</span>
          <div className="min-w-0 flex-1 space-y-2.5">
            <p className="text-sm font-medium leading-snug text-navy-900">{a.text}</p>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <OwnerTag owner={a.owner} />
              <DueDate due={a.due_date} asOf={asOf} />
              {a.deadline_label && <span className="text-xs font-medium text-band-medium">{a.deadline_label}</span>}
            </div>
            <RecordIdList ids={a.record_ids} max={6} />
          </div>
          <Button size="sm" variant="outline" className="self-start" onClick={() => onComplete(a)}>
            Complete
          </Button>
        </li>
      ))}
    </ol>
  );
}

function Ownership({ open, risk }: { open: VesselAction[]; risk: VesselRisk }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {OWNERS.map((owner) => {
        const mine = open.filter((a) => a.owner === owner);
        const components = Object.values(risk.components).filter((c) => c.owner.split("/").map((s) => s.trim()).includes(owner));
        const points = components.reduce((s, c) => s + c.points, 0);
        const next = [...mine].sort((a, b) => a.due_date.localeCompare(b.due_date))[0];
        return (
          <div key={owner} className={cn("rounded-lg border p-4", mine.length ? "bg-card" : "bg-muted/30")}>
            <div className="flex items-center justify-between">
              <OwnerTag owner={owner} />
              <span className="font-display text-2xl font-bold leading-none tabular text-navy-900">{mine.length}</span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              {mine.length ? (
                <>Next due <span className="font-medium text-foreground">{formatDate(next.due_date)}</span></>
              ) : (
                "No open actions"
              )}
            </p>
            {components.length > 0 && (
              <p className="mt-1 text-xs text-muted-foreground">
                Owns {components.map((c) => c.label).join(", ")} · <span className="tabular">{points.toFixed(1)}</span> pts
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Timing({ open, asOf }: { open: VesselAction[]; asOf: string }) {
  if (!open.length) return <p className="text-sm text-muted-foreground">No deadlines.</p>;
  const horizon = Math.max(14, ...open.map((a) => daysBetween(asOf, a.due_date))) + 2;
  const sorted = [...open].sort((a, b) => a.due_date.localeCompare(b.due_date));
  const byDay = new Map<number, VesselAction[]>();
  sorted.forEach((a) => {
    const d = Math.max(0, daysBetween(asOf, a.due_date));
    byDay.set(d, [...(byDay.get(d) ?? []), a]);
  });
  const left = (d: number) => `${(d / horizon) * 100}%`;
  return (
    <div className="space-y-5">
      <div className="relative mx-3 pt-7 pb-8">
        <span className="text-eyebrow absolute top-0 left-0 text-[9px] text-navy-700">Today</span>
        <div className="h-1.5 rounded-full bg-gradient-to-r from-band-high/70 via-band-medium/50 to-silver-100" />
        {[7, 14, 30].filter((d) => d < horizon).map((d) => (
          <div key={d} className="absolute top-[34px] h-3.5 border-l border-dashed border-navy-800/30" style={{ left: left(d) }}>
            <span className="absolute top-4 -translate-x-1/2 text-[10px] text-muted-foreground tabular">{d}d</span>
          </div>
        ))}
        {[...byDay.entries()].map(([d, items]) => (
          <span
            key={d}
            title={items.map((a) => `${a.owner}: ${a.text}`).join("\n")}
            className="absolute top-[19px] flex size-5 -translate-x-1/2 items-center justify-center rounded-full border-2 border-white bg-navy-800 font-heading text-[10px] font-bold text-white shadow"
            style={{ left: left(d) }}
          >
            {items.length}
          </span>
        ))}
      </div>
      <ul className="divide-y rounded-lg border">
        {sorted.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center gap-3 px-4 py-2.5 text-sm">
            <DueDate due={a.due_date} asOf={asOf} className="w-56" />
            <span className="min-w-0 flex-1 truncate text-muted-foreground" title={a.text}>{a.text}</span>
            <span className="text-xs text-muted-foreground">{a.deadline_days}-day rule</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Sections 5–7: what to do, who owns it, and by when. */
export function ActionPlan({ risk, actions, loading }: ActionPlanProps) {
  const [completing, setCompleting] = useState<VesselAction | null>(null);
  const open = (actions ?? []).filter((a) => a.status === "open");

  return (
    <>
      <SectionCard id="action" number={5} title="Action" icon={ClipboardList} subtitle="Generated from overrides and drivers by the rules in rules.yaml">
        {loading ? <Skeleton className="h-40 w-full" /> : <ActionList open={open} asOf={risk.as_of} onComplete={setCompleting} />}
      </SectionCard>
      <div className="grid gap-6 2xl:grid-cols-2">
        <SectionCard id="ownership" number={6} title="Ownership" icon={Users} subtitle="Open actions and score points by department">
          {loading ? <Skeleton className="h-40 w-full" /> : <Ownership open={open} risk={risk} />}
        </SectionCard>
        <SectionCard id="timing" number={7} title="Timing" icon={Hourglass} subtitle={`Deadlines counted from the scoring date, ${formatDate(risk.as_of)}`}>
          {loading ? <Skeleton className="h-40 w-full" /> : <Timing open={open} asOf={risk.as_of} />}
        </SectionCard>
      </div>
      <CompleteActionDialog vesselId={risk.vessel_id} action={completing} onClose={() => setCompleting(null)} />
    </>
  );
}
