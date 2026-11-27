import type { Band, RankingRow, ShadowModelReport } from "@/api/types";
import { BAND_THRESHOLDS } from "@/lib/domain";

export type ScoringMode = "rules" | "model";

const STORAGE_KEY = "esm.shiprisk.scoringMode";

export function readScoringMode(): ScoringMode {
  return localStorage.getItem(STORAGE_KEY) === "model" ? "model" : "rules";
}

export function writeScoringMode(mode: ScoringMode) {
  localStorage.setItem(STORAGE_KEY, mode);
}

export function bandForScore(score: number): Band {
  if (score >= BAND_THRESHOLDS.high) return "High";
  if (score >= BAND_THRESHOLDS.medium) return "Medium";
  return "Low";
}

/** Replace score, band and rank with the registered model. Overrides are a rule mechanism, so they are not applied. */
export function applyModelRanking(rows: RankingRow[], current: ShadowModelReport["current"]): RankingRow[] {
  const byId = new Map(current.map((row) => [row.vessel_id, row]));
  const next = rows.map((row) => {
    const shadow = byId.get(row.vessel_id);
    if (!shadow) return row;
    return {
      ...row,
      score: shadow.shadow_score,
      band: bandForScore(shadow.shadow_score),
      overrides: [],
    };
  });
  next.sort((a, b) => b.score - a.score || a.vessel_id.localeCompare(b.vessel_id));
  return next.map((row, index) => ({ ...row, rank: index + 1 }));
}
