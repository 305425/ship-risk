import { Siren } from "lucide-react";
import type { VesselIssues } from "@/api/types";
import { SectionCard } from "@/components/molecules";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RecordTable, type Column } from "./RecordTable";

const tabs: { key: keyof VesselIssues; label: string; empty: string; columns: Column[] }[] = [
  {
    key: "open_deficiencies",
    label: "Open deficiencies",
    empty: "No open deficiencies",
    columns: [
      { key: "deficiency_id", label: "ID", kind: "id", className: "w-24" },
      { key: "inspection_id", label: "Inspection", kind: "id", className: "w-24" },
      { key: "inspection_date", label: "Found", kind: "date", className: "w-28" },
      { key: "deficiency_category", label: "Category", className: "w-32" },
      { key: "deficiency_description", label: "Description" },
    ],
  },
  {
    key: "overdue_maintenance",
    label: "Overdue maintenance",
    empty: "No overdue maintenance",
    columns: [
      { key: "maintenance_id", label: "ID", kind: "id", className: "w-28" },
      { key: "maintenance_equipment_name", label: "Equipment" },
      { key: "maintenance_due_date", label: "Due", kind: "date", className: "w-28" },
      { key: "maintenance_status", label: "Status", kind: "status", className: "w-24" },
    ],
  },
  {
    key: "unresolved_audit_findings",
    label: "Audit findings",
    empty: "No unresolved audit findings",
    columns: [
      { key: "audit_id", label: "ID", kind: "id", className: "w-24" },
      { key: "audit_finding_description", label: "Finding" },
      { key: "audit_finding_status", label: "Status", kind: "status", className: "w-24" },
    ],
  },
  {
    key: "crew_flags",
    label: "Crew certification",
    empty: "All crew compliant and certified",
    columns: [
      { key: "crew_id", label: "ID", kind: "id", className: "w-20" },
      { key: "rank", label: "Rank" },
      { key: "join_date", label: "Joined", kind: "date", className: "w-28" },
      { key: "rank_experience_months", label: "Months in rank", className: "w-28" },
      { key: "training_status", label: "Training", kind: "status", className: "w-24" },
      { key: "stcw_status", label: "STCW", kind: "status", className: "w-28" },
    ],
  },
];

/** Section 4: the unresolved records behind the score. */
export function CriticalIssuesPanel({ issues, loading }: { issues?: VesselIssues; loading?: boolean }) {
  return (
    <SectionCard id="critical-issues" number={4} title="Critical issues" icon={Siren} subtitle="Unresolved records from the current data version">
      {loading || !issues ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <Tabs defaultValue={tabs.find((t) => issues[t.key].length)?.key ?? tabs[0].key}>
          <TabsList className="mb-3 h-auto flex-wrap justify-start">
            {tabs.map((t) => (
              <TabsTrigger key={t.key} value={t.key} className="gap-1.5">
                {t.label}
                <span className="rounded bg-navy-900/10 px-1.5 font-heading text-[11px] font-semibold tabular">{issues[t.key].length}</span>
              </TabsTrigger>
            ))}
          </TabsList>
          {tabs.map((t) => (
            <TabsContent key={t.key} value={t.key}>
              <RecordTable rows={issues[t.key]} columns={t.columns} empty={t.empty} />
            </TabsContent>
          ))}
        </Tabs>
      )}
    </SectionCard>
  );
}
