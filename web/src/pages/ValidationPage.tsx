import { useState } from "react";
import { Crosshair, Flag, Percent } from "lucide-react";
import { useBacktest, useRiskModel } from "@/api/hooks";
import { ErrorState, PageHeader, StatCard } from "@/components/molecules";
import { BacktestCaveats, BacktestExplainer, BacktestOutcomes, BacktestRounds, RecallCurve, ShadowModelPanel } from "@/components/organisms";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export function ValidationPage() {
  const [topN, setTopN] = useState(2);
  const { data, isLoading, error, refetch, isFetching } = useBacktest(topN);
  const model = useRiskModel();
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Model validation"
        title="Point-in-time backtest"
        description="Would the score have flagged the vessels that were later detained or given major deficiencies?"
        actions={
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Flag the top</span>
            <Select value={String(topN)} onValueChange={(v) => setTopN(Number(v))}>
              <SelectTrigger className="w-20 bg-card"><SelectValue /></SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
              </SelectContent>
            </Select>
            <span className="text-muted-foreground">per round</span>
          </div>
        }
      />

      <BacktestExplainer />

      {isLoading ? (
        <Skeleton className="h-96" />
      ) : error || !data ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <div className={isFetching ? "space-y-6 opacity-70 transition-opacity" : "space-y-6 transition-opacity"}>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              label="Bad outcomes caught"
              value={<>{data.summary.caught}<span className="text-xl text-muted-foreground"> / {data.summary.bad_outcomes}</span></>}
              icon={Crosshair}
              accent={data.summary.caught === data.summary.bad_outcomes ? "low" : "medium"}
              hint={`Flagging the top ${topN} vessels in each round`}
            />
            <StatCard label="Recall" value={pct(data.summary.recall)} icon={Percent} hint="Share of bad outcomes that were flagged" />
            <StatCard label="Flags raised" value={data.summary.flags} icon={Flag} hint={`Precision ${pct(data.summary.precision)}: flags that preceded a bad outcome`} />
          </div>
          <BacktestOutcomes data={data} />
          <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
            <RecallCurve data={data} />
            <BacktestCaveats caveats={data.caveats} components={data.components} />
          </div>
          <BacktestRounds data={data} />
        </div>
      )}

      {model.isLoading ? (
        <Skeleton className="h-96" />
      ) : model.error || !model.data ? (
        <ErrorState error={model.error} onRetry={model.refetch} />
      ) : (
        <ShadowModelPanel data={model.data} />
      )}
    </div>
  );
}
