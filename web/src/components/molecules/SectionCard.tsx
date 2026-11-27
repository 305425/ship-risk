import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface SectionCardProps {
  id?: string;
  number?: number;
  title: string;
  subtitle?: React.ReactNode;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

/** A numbered report section; the numbers match the eight BRD sections on the vessel page. */
export function SectionCard({ id, number, title, subtitle, icon: Icon, actions, children, className, bodyClassName }: SectionCardProps) {
  return (
    <section id={id} className={cn("scroll-mt-24 rounded-xl border bg-card shadow-[0_1px_2px_rgba(15,30,46,0.04)]", className)}>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3.5">
        <div className="flex items-center gap-3">
          {number !== undefined && (
            <span className="font-heading text-xs font-bold text-silver-400 tabular">{String(number).padStart(2, "0")}</span>
          )}
          {Icon && <Icon className="size-4 text-navy-700" />}
          <div>
            <h2 className="text-[15px] font-semibold leading-tight text-navy-900">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        {actions}
      </header>
      <div className={cn("px-5 py-4", bodyClassName)}>{children}</div>
    </section>
  );
}
