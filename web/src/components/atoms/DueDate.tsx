import { CalendarClock } from "lucide-react";
import { daysBetween, formatDate } from "@/lib/domain";
import { cn } from "@/lib/utils";

/** Due date relative to the scoring date (as_of), not the browser clock. */
export function DueDate({ due, asOf, className }: { due: string; asOf: string; className?: string }) {
  const days = daysBetween(asOf, due);
  const tone = days < 0 ? "text-band-high" : days <= 7 ? "text-band-medium" : "text-muted-foreground";
  const rel = days < 0 ? `${-days}d overdue` : days === 0 ? "due today" : `in ${days}d`;
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs", className)}>
      <CalendarClock className="size-3.5 text-muted-foreground" />
      <span className="font-medium text-foreground tabular">{formatDate(due)}</span>
      <span className={cn("tabular", tone)}>{rel}</span>
    </span>
  );
}
