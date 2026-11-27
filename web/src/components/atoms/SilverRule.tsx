import { cn } from "@/lib/utils";

export function SilverRule({ className }: { className?: string }) {
  return <div aria-hidden className={cn("h-[3px] w-full rounded-full bg-silver", className)} />;
}
