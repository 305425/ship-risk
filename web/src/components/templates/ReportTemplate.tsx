import { useEffect, useState } from "react";
import { Eyebrow } from "@/components/atoms";
import { cn } from "@/lib/utils";

export interface ReportSection {
  id: string;
  label: string;
}

interface ReportTemplateProps {
  hero: React.ReactNode;
  sections: ReportSection[];
  children: React.ReactNode;
}

function useActiveSection(ids: string[]) {
  const [active, setActive] = useState(ids[0]);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-80px 0px -60% 0px" },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [ids]);
  return active;
}

/** Hero on top, then the report body with a sticky section index on wide screens. */
export function ReportTemplate({ hero, sections, children }: ReportTemplateProps) {
  const active = useActiveSection(sections.map((s) => s.id));
  return (
    <div className="space-y-6">
      {hero}
      <div className="grid gap-6 xl:grid-cols-[180px_minmax(0,1fr)]">
        <nav className="sticky top-20 hidden h-fit space-y-1 xl:block" aria-label="Report sections">
          <Eyebrow className="mb-2 px-3">Report</Eyebrow>
          {sections.map((s, i) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className={cn(
                "flex items-center gap-2.5 rounded-md border-l-2 px-3 py-1.5 text-[13px] transition-colors",
                active === s.id ? "border-navy-700 bg-card font-medium text-navy-900 shadow-sm" : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <span className="font-heading text-[10px] font-bold text-silver-400 tabular">{String(i + 1).padStart(2, "0")}</span>
              {s.label}
            </a>
          ))}
        </nav>
        <div className="min-w-0 space-y-6">{children}</div>
      </div>
    </div>
  );
}
