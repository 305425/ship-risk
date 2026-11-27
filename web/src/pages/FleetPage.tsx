import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Eye, ShieldCheck, Ship, UploadCloud } from "lucide-react";
import { useActiveRanking, useRiskModel } from "@/api/hooks";
import { useScoringMode } from "@/providers/ScoringModeProvider";
import type { Band } from "@/api/types";
import { BandFilter, ErrorState, PageHeader, SearchInput, StatCard, type BandFilterValue } from "@/components/molecules";
import { FleetHorizon, FleetRankingTable, ScoreFitChart } from "@/components/organisms";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function FleetPage() {
  const { mode } = useScoringMode();
  const { data, isLoading, error, refetch } = useActiveRanking();
  const model = useRiskModel();
  const [band, setBand] = useState<BandFilterValue>("All");
  const [search, setSearch] = useState("");

  const counts = useMemo(() => {
    const c: Record<Band, number> = { High: 0, Medium: 0, Low: 0 };
    (data ?? []).forEach((r) => c[r.band]++);
    return c;
  }, [data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data ?? []).filter(
      (r) =>
        (band === "All" || r.band === band) &&
        (!q || r.vessel_id.toLowerCase().includes(q) || (r.vessel_name ?? "").toLowerCase().includes(q)),
    );
  }, [data, band, search]);

  const overrides = (data ?? []).filter((r) => r.overrides.length > 0).length;
  const avg = data?.length ? data.reduce((s, r) => s + r.score, 0) / data.length : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Fleet overview"
        title="Detention risk ranking"
        description={
          mode === "model"
            ? "Every vessel scored 0–100 by the registered logistic regression. High is 60 or above and Medium is 35 or above, the same cutoffs as the rules. Actions and the component breakdown stay with the rules."
            : "Every vessel scored 0–100 from inspection history, deficiencies, maintenance, crew and audit records. Overrides force a vessel to High regardless of score."
        }
        actions={
          <Button asChild variant="outline">
            <Link to="/upload"><UploadCloud className="size-4" /> Upload data</Link>
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-28" />)}
          </div>
          <Skeleton className="h-56" />
          <Skeleton className="h-96" />
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Vessels scored" value={data!.length} icon={Ship} hint={`Fleet average ${avg.toFixed(1)}`} />
            <StatCard
              label="High · act now"
              value={counts.High}
              icon={AlertTriangle}
              accent="high"
              hint={mode === "model" ? "Model score 60 or above" : `${overrides} forced by an override`}
            />
            <StatCard label="Medium · watch" value={counts.Medium} icon={Eye} accent="medium" hint="Score 35 to 59" />
            <StatCard label="Low · routine" value={counts.Low} icon={ShieldCheck} accent="low" hint="Score under 35" />
          </div>

          <FleetHorizon rows={data!} />

          {model.isLoading ? (
            <Skeleton className="h-80" />
          ) : model.data ? (
            <ScoreFitChart rows={model.data.current} />
          ) : (
            <ErrorState error={model.error} onRetry={model.refetch} />
          )}

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <BandFilter value={band} onChange={setBand} counts={counts} total={data!.length} />
              <SearchInput value={search} onChange={setSearch} placeholder="Search vessel name or ID" className="w-full sm:w-72" />
            </div>
            <FleetRankingTable rows={filtered} />
          </div>
        </>
      )}
    </div>
  );
}
