import type { Band } from "@/api/types";
import { bandStyle } from "@/lib/domain";
import { cn } from "@/lib/utils";
import { Pennant } from "./Pennant";

interface BandBadgeProps {
  band: Band;
  size?: "sm" | "md" | "lg";
  showHint?: boolean;
  className?: string;
}

const sizes = {
  sm: "h-5 px-1.5 text-[11px] gap-1",
  md: "h-6 px-2 text-xs gap-1.5",
  lg: "h-8 px-3 text-sm gap-2",
};

export function BandBadge({ band, size = "md", showHint = false, className }: BandBadgeProps) {
  const s = bandStyle[band];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md font-heading font-semibold uppercase tracking-wider ring-1 ring-inset",
        s.soft,
        s.text,
        s.ring,
        sizes[size],
        className,
      )}
    >
      <Pennant className={size === "lg" ? "size-4" : "size-3"} />
      {band}
      {showHint && <span className="font-sans font-medium normal-case tracking-normal opacity-75">· {s.label}</span>}
    </span>
  );
}
