import { Anchor, ClipboardCheck, Users, Wrench, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const owners: Record<string, { icon: LucideIcon; className: string }> = {
  Marine: { icon: Anchor, className: "bg-navy-50 text-navy-800 ring-navy-100" },
  Technical: { icon: Wrench, className: "bg-slate-100 text-slate-700 ring-slate-200" },
  Crewing: { icon: Users, className: "bg-sky-50 text-sky-800 ring-sky-100" },
  HSQE: { icon: ClipboardCheck, className: "bg-teal-50 text-teal-800 ring-teal-100" },
};

export function OwnerTag({ owner, className }: { owner: string; className?: string }) {
  const primary = owner.split("/")[0].trim();
  const cfg = owners[primary] ?? owners.Marine;
  const Icon = cfg.icon;
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-md px-2 text-xs font-medium ring-1 ring-inset",
        cfg.className,
        className,
      )}
    >
      <Icon className="size-3.5" />
      {owner}
    </span>
  );
}
