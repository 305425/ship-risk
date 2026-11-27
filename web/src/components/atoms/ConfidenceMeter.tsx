import type { Confidence } from "@/api/types";
import { cn } from "@/lib/utils";

const level: Record<Confidence, number> = { Low: 1, Medium: 2, High: 3 };

/** Signal-strength bars: how much the score can be trusted, not how risky the vessel is. */
export function ConfidenceMeter({ value, showLabel = true, className }: { value: Confidence; showLabel?: boolean; className?: string }) {
  const n = level[value];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs text-muted-foreground", className)} title={`${value} confidence`}>
      <span className="flex h-3 items-end gap-[2px]" aria-hidden>
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            className={cn("w-[3px] rounded-[1px]", i <= n ? "bg-navy-700" : "bg-silver-200")}
            style={{ height: `${i * 4}px` }}
          />
        ))}
      </span>
      {showLabel && <span>{value}</span>}
    </span>
  );
}
