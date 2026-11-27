import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronRight, ShieldAlert } from "lucide-react";
import type { RankingRow } from "@/api/types";
import { BandBadge, ConfidenceMeter } from "@/components/atoms";
import { EmptyState } from "@/components/molecules";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { bandStyle, componentLabel } from "@/lib/domain";
import { cn } from "@/lib/utils";

type SortKey = "rank" | "vessel" | "score";

function SortHeader({ label, k, sort, onSort, className }: { label: string; k: SortKey; sort: { key: SortKey; asc: boolean }; onSort: (k: SortKey) => void; className?: string }) {
  const active = sort.key === k;
  const Icon = !active ? ArrowUpDown : sort.asc ? ArrowUp : ArrowDown;
  return (
    <TableHead className={className}>
      <button type="button" onClick={() => onSort(k)} className={cn("inline-flex items-center gap-1 hover:text-foreground", active && "text-foreground")}>
        {label}
        <Icon className="size-3" />
      </button>
    </TableHead>
  );
}

export function FleetRankingTable({ rows }: { rows: RankingRow[] }) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: "rank", asc: true });

  const sorted = useMemo(() => {
    const out = [...rows];
    const dir = sort.asc ? 1 : -1;
    out.sort((a, b) => {
      if (sort.key === "vessel") return dir * (a.vessel_name ?? a.vessel_id).localeCompare(b.vessel_name ?? b.vessel_id);
      if (sort.key === "score") return dir * (a.score - b.score);
      return dir * (a.rank - b.rank);
    });
    return out;
  }, [rows, sort]);

  const onSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, asc: !s.asc } : { key, asc: key !== "score" }));

  if (!rows.length) return <EmptyState title="No vessels match" description="Try a different band filter or search." />;

  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Table>
        <TableHeader className="bg-navy-50/60">
          <TableRow className="hover:bg-transparent">
            <SortHeader label="#" k="rank" sort={sort} onSort={onSort} className="w-14 pl-5" />
            <SortHeader label="Vessel" k="vessel" sort={sort} onSort={onSort} />
            <SortHeader label="Score" k="score" sort={sort} onSort={onSort} className="w-44" />
            <TableHead className="w-28">Band</TableHead>
            <TableHead className="hidden w-28 md:table-cell">Confidence</TableHead>
            <TableHead className="hidden lg:table-cell">Top drivers</TableHead>
            <TableHead className="w-8" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((r) => (
            <TableRow
              key={r.vessel_id}
              onClick={() => navigate(`/vessels/${r.vessel_id}`)}
              className="group cursor-pointer"
            >
              <TableCell className="pl-5 font-heading text-sm font-semibold text-muted-foreground tabular">{r.rank}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-navy-900">{r.vessel_name ?? "Unknown vessel"}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{r.vessel_id}</p>
                  </div>
                  {r.overrides.length > 0 && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex items-center gap-1 rounded bg-band-high-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-band-high">
                          <ShieldAlert className="size-3" /> {r.overrides.length}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p className="mb-1 font-medium">Overrides forcing High</p>
                        <ul className="list-disc space-y-0.5 pl-4 text-xs">
                          {r.overrides.map((o) => <li key={o}>{o}</li>)}
                        </ul>
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-3">
                  <span className="w-10 font-heading text-base font-semibold tabular">{r.score.toFixed(1)}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-silver-100">
                    <div className={cn("h-full rounded-full", bandStyle[r.band].bg)} style={{ width: `${r.score}%` }} />
                  </div>
                </div>
              </TableCell>
              <TableCell><BandBadge band={r.band} size="sm" /></TableCell>
              <TableCell className="hidden md:table-cell"><ConfidenceMeter value={r.confidence} /></TableCell>
              <TableCell className="hidden max-w-md lg:table-cell">
                <ul className="space-y-0.5">
                  {r.drivers.slice(0, 2).map((d) => (
                    <li key={d.feature} className="flex items-baseline gap-2 text-xs">
                      <span className="w-24 shrink-0 text-[10px] font-semibold tracking-wide text-navy-600 uppercase">{componentLabel(d.component)}</span>
                      <span className="truncate text-muted-foreground" title={d.text}>{d.text}</span>
                    </li>
                  ))}
                </ul>
              </TableCell>
              <TableCell className="pr-4">
                <ChevronRight className="size-4 text-silver-400 transition-transform group-hover:translate-x-0.5 group-hover:text-navy-700" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
