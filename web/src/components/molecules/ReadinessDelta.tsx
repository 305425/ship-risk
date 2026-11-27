import { ArrowRight, TrendingDown, TrendingUp } from "lucide-react";
import type { Readiness } from "@/api/types";
import { BandBadge } from "@/components/atoms";
import { cn } from "@/lib/utils";

export function ReadinessDelta({ readiness, className }: { readiness: Readiness; className?: string }) {
  const delta = readiness.after.score - readiness.before.score;
  const better = delta < 0;
  const Trend = better ? TrendingDown : TrendingUp;
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <BandBadge band={readiness.before.band} size="sm" />
      <span className="font-heading text-sm font-semibold tabular">{readiness.before.score.toFixed(0)}</span>
      <ArrowRight className="size-3.5 text-muted-foreground" />
      <BandBadge band={readiness.after.band} size="sm" />
      <span className="font-heading text-sm font-semibold tabular">{readiness.after.score.toFixed(0)}</span>
      <span
        className={cn(
          "inline-flex items-center gap-1 text-xs font-medium tabular",
          better ? "text-band-low" : delta > 0 ? "text-band-high" : "text-muted-foreground",
        )}
      >
        <Trend className="size-3.5" />
        {delta > 0 ? "+" : ""}
        {delta.toFixed(1)}
      </span>
    </div>
  );
}
