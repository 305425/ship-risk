import type { IssueRecord } from "@/api/types";
import { RecordId } from "@/components/atoms";
import { EmptyState } from "@/components/molecules";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/domain";
import { cn } from "@/lib/utils";

export interface Column {
  key: string;
  label: string;
  kind?: "id" | "date" | "status" | "text";
  className?: string;
}

const statusTone: Record<string, string> = {
  Open: "bg-band-medium-soft text-band-medium",
  Overdue: "bg-band-high-soft text-band-high",
  Pending: "bg-band-medium-soft text-band-medium",
  Expired: "bg-band-high-soft text-band-high",
  "Expiring Soon": "bg-band-medium-soft text-band-medium",
};

function Cell({ value, kind }: { value: IssueRecord[string]; kind?: Column["kind"] }) {
  if (value === null || value === undefined || value === "") return <span className="text-muted-foreground">—</span>;
  if (kind === "id") return <RecordId id={String(value)} />;
  if (kind === "date") return <span className="tabular">{formatDate(String(value))}</span>;
  if (kind === "status") {
    return (
      <span className={cn("inline-flex rounded px-1.5 py-0.5 text-[11px] font-semibold", statusTone[String(value)] ?? "bg-muted text-muted-foreground")}>
        {value}
      </span>
    );
  }
  return <>{value}</>;
}

export function RecordTable({ rows, columns, empty }: { rows: IssueRecord[]; columns: Column[]; empty: string }) {
  if (!rows.length) return <EmptyState title={empty} className="py-8" />;
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow className="hover:bg-transparent">
            {columns.map((c) => (
              <TableHead key={c.key} className={cn("text-xs", c.className)}>{c.label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => (
            <TableRow key={i}>
              {columns.map((c) => (
                <TableCell key={c.key} className={cn("text-[13px] whitespace-normal", c.className)}>
                  <Cell value={r[c.key]} kind={c.kind} />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
