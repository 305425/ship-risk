import { useParams } from "react-router-dom";
import { useActiveRanking, useVesselActions, useVesselHistory, useVesselIssues, useVesselRisk } from "@/api/hooks";
import { useScoringMode } from "@/providers/ScoringModeProvider";
import { ErrorState } from "@/components/molecules";
import { ActionPlan, CriticalIssuesPanel, EvidencePanel, ReadinessPanel, VesselHero, WhyPanel } from "@/components/organisms";
import { ReportTemplate, type ReportSection } from "@/components/templates";
import { Skeleton } from "@/components/ui/skeleton";

const SECTIONS: ReportSection[] = [
  { id: "current-risk", label: "Current risk" },
  { id: "why", label: "Why" },
  { id: "evidence", label: "Evidence" },
  { id: "critical-issues", label: "Critical issues" },
  { id: "action", label: "Action" },
  { id: "ownership", label: "Ownership" },
  { id: "timing", label: "Timing" },
  { id: "readiness", label: "Readiness" },
];

export function VesselPage() {
  const { vesselId = "" } = useParams();
  const { mode } = useScoringMode();
  const risk = useVesselRisk(vesselId);
  const ranking = useActiveRanking();
  const issues = useVesselIssues(vesselId);
  const actions = useVesselActions(vesselId);
  const history = useVesselHistory(vesselId);

  if (risk.isLoading || (mode === "model" && ranking.isLoading)) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-80 rounded-2xl" />
        <Skeleton className="h-72" />
      </div>
    );
  }
  if (risk.error || !risk.data || (mode === "model" && ranking.error)) {
    return <ErrorState error={risk.error ?? ranking.error} onRetry={() => { risk.refetch(); ranking.refetch(); }} />;
  }

  const ranked = ranking.data?.find((r) => r.vessel_id === vesselId);
  const shown = mode === "model" && ranked ? { ...risk.data, score: ranked.score, band: ranked.band } : risk.data;

  return (
    <ReportTemplate hero={<VesselHero risk={shown} rank={ranked?.rank} fleetSize={ranking.data?.length} />} sections={SECTIONS}>
      <WhyPanel risk={shown} />
      <EvidencePanel vesselId={vesselId} />
      <CriticalIssuesPanel issues={issues.data} loading={issues.isLoading} />
      <ActionPlan risk={risk.data} actions={actions.data} loading={actions.isLoading} />
      <ReadinessPanel history={history.data} actions={actions.data} loading={history.isLoading || actions.isLoading} />
    </ReportTemplate>
  );
}
