import { useNavigate } from "react-router-dom";
import type { ShadowModelReport, ShadowOutcome } from "@/api/types";
import { BandBadge } from "@/components/atoms";
import { SectionCard } from "@/components/molecules";
import { ScoreFitChart } from "./ScoreFit";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function outcomeText(item: ShadowOutcome) {
  return `${item.vessel_id} ${item.outcome.toLowerCase()} ranked ${item.rank}`;
}

function Check({ title, detail, outcomes }: { title: string; detail: string; outcomes: ShadowOutcome[] }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mt-1 text-sm text-navy-900">{detail}</p>
      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
        {outcomes.map((item) => (
          <li key={item.inspection_id}>{outcomeText(item)}</li>
        ))}
      </ul>
    </div>
  );
}

export function ShadowModelPanel({ data }: { data: ShadowModelReport }) {
  const navigate = useNavigate();
  const recall = (caught: number, total: number) => `${caught} of ${total}`;

  return (
    <div className="space-y-6">
      <SectionCard
        title="Shadow model"
        subtitle="Logistic regression on the inspection and deficiency features the rules already compute. Choose Model in the top bar to rank the fleet with this score. Actions stay with the rules."
      >
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Trained on {data.rows} inspections that already had some history, {data.positives} of which ended in major deficiencies or detention.
            The shadow score stretches the model's log-odds from 0 to 100 across the current fleet.
          </p>
          <p className="text-sm text-navy-900">
            MLflow <span className="font-mono">{data.registry.name}</span> version {data.registry.version}
            {data.registry.trigger_ref ? `, saved after upload ${data.registry.trigger_ref}` : `, saved on ${data.registry.trigger}`}.
          </p>
          <p className="break-all font-mono text-[11px] text-muted-foreground">{data.registry.model_uri}</p>
          <div className="grid gap-3 lg:grid-cols-3">
            <Check
              title="In sample"
              detail={`Top 3 catches ${recall(data.in_sample.recall_at_3.caught, data.in_sample.recall_at_3.bad_outcomes)}.`}
              outcomes={data.in_sample.bad_outcomes}
            />
            <Check
              title="Forward check"
              detail={`Trained before round ${data.forward.trained_on_rounds_before}. Top 3 catches ${recall(data.forward.recall_at_3.caught, data.forward.recall_at_3.bad_outcomes)}.`}
              outcomes={data.forward.bad_outcomes}
            />
            <Check
              title="Leave one vessel out"
              detail={`Top 3 catches ${recall(data.leave_one_vessel_out.recall_at_3.caught, data.leave_one_vessel_out.recall_at_3.bad_outcomes)}.`}
              outcomes={data.leave_one_vessel_out.bad_outcomes}
            />
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">What the model weighs</p>
            <ul className="flex flex-wrap gap-2">
              {data.coefficients.map((item) => (
                <li key={item.feature} className="rounded-full border px-3 py-1 text-xs text-navy-900">
                  {item.label}
                  <span className="ml-1 font-heading tabular text-muted-foreground">
                    {item.coefficient > 0 ? "+" : ""}
                    {item.coefficient.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </SectionCard>

      <ScoreFitChart rows={data.current} />

      <SectionCard title="Current shadow ranking" subtitle="The Model setting uses this score, with High from 60 and Medium from 35." bodyClassName="px-0 pb-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-5">Rank</TableHead>
              <TableHead>Vessel</TableHead>
              <TableHead className="text-right">Shadow</TableHead>
              <TableHead className="text-right">Rule score</TableHead>
              <TableHead>Rule band</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.current.map((row) => (
              <TableRow key={row.vessel_id} onClick={() => navigate(`/vessels/${row.vessel_id}`)} className="cursor-pointer">
                <TableCell className="pl-5 font-heading tabular text-muted-foreground">{row.rank}</TableCell>
                <TableCell>
                  <p className="font-medium text-navy-900">{row.vessel_name}</p>
                  <p className="font-mono text-[11px] text-muted-foreground">{row.vessel_id}</p>
                </TableCell>
                <TableCell className="text-right font-heading font-semibold tabular">{row.shadow_score.toFixed(0)}</TableCell>
                <TableCell className="text-right font-heading tabular">{row.rule_score.toFixed(0)}</TableCell>
                <TableCell><BandBadge band={row.rule_band} size="sm" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </SectionCard>

      <SectionCard title="What this model cannot show">
        <ul className="space-y-2 text-sm text-muted-foreground">
          {data.caveats.map((caveat) => (
            <li key={caveat} className="flex gap-2">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-band-medium" />
              <span>{caveat}</span>
            </li>
          ))}
        </ul>
      </SectionCard>
    </div>
  );
}
