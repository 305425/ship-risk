import type { Driver } from "@/api/types";
import { OwnerTag } from "@/components/atoms";
import { componentLabel } from "@/lib/domain";
import { cn } from "@/lib/utils";
import { RecordIdList } from "./RecordIdList";

interface DriverItemProps {
  driver: Driver;
  index: number;
  compact?: boolean;
}

export function DriverItem({ driver, index, compact }: DriverItemProps) {
  return (
    <div className={cn("flex gap-3", compact ? "py-1.5" : "py-3")}>
      <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-navy-900 font-heading text-[11px] font-bold text-white">
        {index + 1}
      </span>
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <p className="text-sm font-medium leading-snug text-foreground">{driver.text}</p>
          <span className="shrink-0 font-heading text-sm font-semibold text-navy-700 tabular">+{driver.points.toFixed(1)} pts</span>
        </div>
        {!compact && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-eyebrow text-muted-foreground">{componentLabel(driver.component)}</span>
            <OwnerTag owner={driver.owner} />
            <RecordIdList ids={driver.record_ids} />
          </div>
        )}
      </div>
    </div>
  );
}
