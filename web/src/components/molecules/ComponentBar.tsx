import type { ScoreComponent } from "@/api/types";
import { OwnerTag } from "@/components/atoms";
import { cn } from "@/lib/utils";

/** One score component: points earned against its maximum weight. */
export function ComponentBar({ component, className }: { component: ScoreComponent; className?: string }) {
  const pct = component.max_points ? (component.points / component.max_points) * 100 : 0;
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{component.label}</span>
        <span className="font-heading text-sm tabular">
          <span className="font-semibold text-foreground">{component.points.toFixed(1)}</span>
          <span className="text-muted-foreground"> / {component.max_points}</span>
        </span>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-silver-100">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-navy-700 to-navy-600 transition-[width] duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
      <OwnerTag owner={component.owner} className="h-5 text-[11px]" />
    </div>
  );
}
