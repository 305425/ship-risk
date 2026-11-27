import { useMemo } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { applyModelRanking } from "@/lib/scoringMode";
import { useScoringMode } from "@/providers/ScoringModeProvider";
import { api } from "./client";
import type { EvidenceQuery } from "./types";

export const keys = {
  health: ["health"] as const,
  ranking: ["ranking"] as const,
  vessel: (id: string) => ["vessel", id] as const,
  uploads: ["uploads"] as const,
  uploadDiff: (id: number) => ["uploads", id, "diff"] as const,
  backtest: (n: number) => ["backtest", n] as const,
  riskModel: ["risk-model"] as const,
  indexStatus: ["index-status"] as const,
};

export const useHealth = () =>
  useQuery({ queryKey: keys.health, queryFn: api.health, refetchInterval: 30_000, retry: false });

export const useRanking = () => useQuery({ queryKey: keys.ranking, queryFn: api.ranking });

/** Fleet ranking for the selected approach. Model mode swaps in the registered shadow score. */
export function useActiveRanking() {
  const { mode } = useScoringMode();
  const ranking = useRanking();
  const model = useQuery({
    queryKey: keys.riskModel,
    queryFn: api.riskModel,
    enabled: mode === "model",
  });
  const data = useMemo(() => {
    if (!ranking.data) return undefined;
    if (mode !== "model") return ranking.data;
    if (!model.data) return undefined;
    return applyModelRanking(ranking.data, model.data.current);
  }, [ranking.data, mode, model.data]);

  return {
    data,
    isLoading: ranking.isLoading || (mode === "model" && model.isLoading),
    error: ranking.error ?? (mode === "model" ? model.error : null),
    refetch: () => {
      void ranking.refetch();
      if (mode === "model") void model.refetch();
    },
  };
}

export const useVesselRisk = (id: string) =>
  useQuery({ queryKey: [...keys.vessel(id), "risk"], queryFn: () => api.vesselRisk(id) });

export const useVesselHistory = (id: string) =>
  useQuery({ queryKey: [...keys.vessel(id), "history"], queryFn: () => api.vesselHistory(id) });

export const useVesselIssues = (id: string) =>
  useQuery({ queryKey: [...keys.vessel(id), "issues"], queryFn: () => api.vesselIssues(id) });

export const useVesselActions = (id: string) =>
  useQuery({ queryKey: [...keys.vessel(id), "actions"], queryFn: () => api.vesselActions(id, true) });

export const useUploads = () => useQuery({ queryKey: keys.uploads, queryFn: api.uploads });

export const useUploadDiff = (id: number | null) =>
  useQuery({ queryKey: keys.uploadDiff(id ?? -1), queryFn: () => api.uploadDiff(id!), enabled: id !== null });

export const useBacktest = (topN: number) =>
  useQuery({ queryKey: keys.backtest(topN), queryFn: () => api.backtest(topN), placeholderData: keepPreviousData });

export const useRiskModel = () => useQuery({ queryKey: keys.riskModel, queryFn: api.riskModel });

export const useRecord = (id: string | null) =>
  useQuery({ queryKey: ["record", id], queryFn: () => api.record(id!), enabled: id !== null });

export const useIndexStatus = () =>
  useQuery({ queryKey: keys.indexStatus, queryFn: api.indexStatus, retry: false, staleTime: 60_000 });

export function useCompleteAction(vesselId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, evidence }: { actionId: number; evidence: string }) =>
      api.completeAction(vesselId, actionId, evidence),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.vessel(vesselId) });
      qc.invalidateQueries({ queryKey: keys.ranking });
    },
  });
}

export function useUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.upload,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.ranking });
      qc.invalidateQueries({ queryKey: keys.uploads });
      qc.invalidateQueries({ queryKey: ["vessel"] });
      qc.invalidateQueries({ queryKey: ["backtest"] });
      qc.invalidateQueries({ queryKey: keys.riskModel });
    },
  });
}

export function useEvidence(vesselId: string) {
  return useMutation({ mutationFn: (q: EvidenceQuery) => api.evidence(vesselId, q) });
}
