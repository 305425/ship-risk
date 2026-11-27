import type { LucideIcon } from "lucide-react";
import { Eyebrow } from "@/components/atoms";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  accent?: "navy" | "high" | "medium" | "low";
  className?: string;
}

const accents = {
  navy: "before:bg-navy-700",
  high: "before:bg-band-high",
  medium: "before:bg-band-medium",
  low: "before:bg-band-low",
};

export function StatCard({ label, value, hint, icon: Icon, accent = "navy", className }: StatCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border bg-card px-5 py-4 shadow-[0_1px_0_rgba(15,30,46,0.04)]",
        "before:absolute before:inset-y-0 before:left-0 before:w-1",
        accents[accent],
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <Eyebrow>{label}</Eyebrow>
        {Icon && <Icon className="size-4 text-silver-400" />}
      </div>
      <div className="mt-2 font-display text-3xl font-semibold leading-none tabular text-foreground">{value}</div>
      {hint && <div className="mt-2 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
