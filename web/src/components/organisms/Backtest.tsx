import { Fragment } from "react";
import { Link } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Flag, Info, Target, TriangleAlert } from "lucide-react";
import type { Backtest, BacktestRound } from "@/api/types";
import { Eyebrow, Pennant, RecordId } from "@/components/atoms";
import { SectionCard } from "@/components/molecules";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip as UiTooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { bandStyle, formatDate } from "@/lib/domain";
import { cn } from "@/lib/utils";

export function BacktestExplainer() {
  return (
    <div className="grid gap-4 rounded-xl border border-navy-100 bg-navy-50/50 p-5 md:grid-cols-[auto_1fr]">
      <span className="flex size-10 items-center justify-center rounded-full bg-navy-900 text-white">
        <Info className="size-5" />
      </span>
      <div className="space-y-2 text-sm leading-relaxed text-navy-900">
        <p className="font-heading font-semibold">What this page shows</p>
        <p className="text-muted-foreground">
          A backtest checks the score against history. For each past inspection round we hide everything that happened on or after
          the inspection, score each vessel with only what was known before, and rank them. If the vessels that went on to be detained
          or get major deficiencies sat at the top of those rankings, the score would have warned us in time.
        </p>
      </div>
    </div>
  );
}

export function BacktestOutcomes({ data }: { data: Backtest }) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {data.bad_outcomes.map((o) => (
        <div
          key={o.inspection_id}
          className={cn("relative overflow-hidden rounded-xl border bg-card p-4", o.flagged ? "ring-2 ring-band-low/30" : "ring-2 ring-band-high/25")}
        >
          <div className="flex items-start justify-between">
            <div>
              <Eyebrow>Round {o.round} · {formatDate(o.inspection_date)}</Eyebrow>
              <Link to={`/vessels/${o.vessel_id}`} className="mt-1 block font-heading text-lg font-bold text-navy-900 hover:underline">
                {o.vessel_id}
              </Link>
              <p className="text-sm text-muted-foreground">{o.outcome}</p>
            </div>
            <div className="text-right">
              <p className="font-display text-4xl font-bold leading-none tabular text-navy-900">#{o.rank}</p>
              {o.tied_with > 0 && <p className="mt-1 text-[11px] text-muted-foreground">tied with {o.tied_with}</p>}
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <RecordId id={o.inspection_id} />
            <span className={cn("inline-flex items-center gap-1 text-xs font-semibold", o.flagged ? "text-band-low" : "text-band-high")}>
              <Flag className="size-3.5" /> {o.flagged ? `Caught in top ${data.top_n}` : `Missed at top ${data.top_n}`}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export function RecallCurve({ data }: { data: Backtest }) {
  const rows = data.recall_curve.map((s) => ({
    n: `Top ${s.top_n}`,
    recall: Math.round((s.recall ?? 0) * 100),
    precision: Math.round((s.precision ?? 0) * 100),
    flags: s.flags,
  }));
  return (
    <SectionCard title="Shortlist size vs. catch rate" icon={Target} subtitle="Flagging more vessels per round catches more bad outcomes, but more flags are false alarms">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ left: -12, right: 8, top: 8 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis dataKey="n" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="pct" domain={[0, 100]} unit="%" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="flags" orientation="right" hide />
            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid var(--border)", fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar yAxisId="flags" dataKey="flags" name="Vessels flagged" fill="var(--silver-200)" radius={[4, 4, 0, 0]} barSize={28} />
            <Line yAxisId="pct" type="monotone" dataKey="recall" name="Recall %" stroke="var(--navy-700)" strokeWidth={2.5} dot={{ r: 4 }} />
            <Line yAxisId="pct" type="monotone" dataKey="precision" name="Precision %" stroke={bandStyle.Medium.hex} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

function RoundColumn({ round }: { round: BacktestRound }) {
  return (
    <ol className="space-y-1">
      {round.ranking.map((r) => (
        <li key={r.vessel_id}>
          <UiTooltip>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  "flex items-center gap-2 rounded px-2 py-1 text-xs",
                  r.bad_outcome ? "bg-band-high-soft font-semibold text-band-high" : r.flagged ? "bg-navy-50 text-navy-900" : "text-muted-foreground",
                )}
              >
                <span className="w-5 font-heading tabular">{r.rank}</span>
                <span className="font-mono">{r.vessel_id}</span>
                {r.bad_outcome && <Pennant className="size-3" color={bandStyle.High.hex} />}
                <span className="ml-auto font-heading tabular">{r.score.toFixed(1)}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="font-medium">{r.vessel_id} · {r.inspection_id} · {r.outcome}</p>
              {r.top_driver && <p className="text-xs opacity-80">{r.top_driver}</p>}
            </TooltipContent>
          </UiTooltip>
        </li>
      ))}
    </ol>
  );
}

export function BacktestRounds({ data }: { data: Backtest }) {
  return (
    <SectionCard
      title="Rankings by inspection round"
      subtitle={`Shaded rows were flagged (top ${data.top_n}); red rows went on to a bad outcome`}
      bodyClassName="overflow-x-auto"
    >
      <div className="grid min-w-[720px] gap-4" style={{ gridTemplateColumns: `repeat(${data.rounds.length}, minmax(0, 1fr))` }}>
        {data.rounds.map((r) => (
          <Fragment key={r.round}>
            <div className="space-y-2">
              <div className="border-b pb-2">
                <p className="font-heading text-sm font-semibold text-navy-900">Round {r.round}</p>
                <p className="text-[11px] text-muted-foreground">
                  {formatDate(r.date_range[0])} – {formatDate(r.date_range[1])}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground tabular">
                  {r.flagged} flagged · {r.bad_outcomes_flagged}/{r.bad_outcomes} caught
                </p>
              </div>
              <RoundColumn round={r} />
            </div>
          </Fragment>
        ))}
      </div>
    </SectionCard>
  );
}

export function BacktestCaveats({ caveats, components }: { caveats: string[]; components: string[] }) {
  return (
    <SectionCard title="Caveats" icon={TriangleAlert} subtitle={`Components tested: ${components.join(", ")}`}>
      <Table>
        <TableHeader className="sr-only">
          <TableRow><TableHead>Caveat</TableHead></TableRow>
        </TableHeader>
        <TableBody>
          {caveats.map((c) => (
            <TableRow key={c} className="hover:bg-transparent">
              <TableCell className="py-2.5 text-sm whitespace-normal text-muted-foreground">
                <span className="mr-2 inline-block size-1.5 rounded-full bg-band-medium align-middle" />
                {c}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </SectionCard>
  );
}
