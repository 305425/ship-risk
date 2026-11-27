import { cn } from "@/lib/utils";

/** A small waving signal pennant, echoing the flag in the ESM logo. */
export function Pennant({ className, color = "currentColor" }: { className?: string; color?: string }) {
  return (
    <svg viewBox="0 0 16 12" className={cn("size-3.5 shrink-0", className)} aria-hidden>
      <path d="M1 1v10" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
      <path d="M2 1.4c3-1.2 5 1 8 0 1.4-.5 2.6-.6 4 .1v5.6c-1.4-.7-2.6-.6-4-.1-3 1-5-1.2-8 0V1.4Z" fill={color} />
    </svg>
  );
}
