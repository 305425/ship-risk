import { cn } from "@/lib/utils";

const tones = {
  ok: "bg-band-low",
  warn: "bg-band-medium",
  bad: "bg-band-high",
  idle: "bg-silver-400",
};

export function StatusDot({ tone, pulse = false, className }: { tone: keyof typeof tones; pulse?: boolean; className?: string }) {
  return (
    <span className={cn("relative inline-flex size-2 shrink-0", className)}>
      {pulse && <span className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-60", tones[tone])} />}
      <span className={cn("relative inline-flex size-2 rounded-full", tones[tone])} />
    </span>
  );
}
