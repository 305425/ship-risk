import { useNavigate } from "react-router-dom";
import type { RankingRow } from "@/api/types";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BAND_THRESHOLDS, bandStyle } from "@/lib/domain";
import { cn } from "@/lib/utils";

/** Every vessel as one column on a 0–100 scale, with the band thresholds drawn across. */
export function FleetHorizon({ rows }: { rows: RankingRow[] }) {
  const navigate = useNavigate();
  return (
    <div className="relative rounded-xl border bg-card px-5 pt-4 pb-3">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-[15px] font-semibold text-navy-900">Fleet horizon</h2>
          <p className="text-xs text-muted-foreground">Each column is one vessel, ranked by risk score. Click a column to open it.</p>
        </div>
        <div className="hidden items-center gap-4 text-[11px] text-muted-foreground sm:flex">
          <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 border-t border-dashed border-band-high" /> High ≥ {BAND_THRESHOLDS.high}</span>
          <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 border-t border-dashed border-band-medium" /> Medium ≥ {BAND_THRESHOLDS.medium}</span>
        </div>
      </div>
      <div className="relative h-40">
        {[BAND_THRESHOLDS.high, BAND_THRESHOLDS.medium].map((t) => (
          <div
            key={t}
            className={cn("absolute inset-x-0 border-t border-dashed", t === BAND_THRESHOLDS.high ? "border-band-high/50" : "border-band-medium/50")}
            style={{ bottom: `${t}%` }}
          >
            <span className="absolute -top-2 right-0 bg-card pl-1 font-heading text-[10px] font-semibold text-muted-foreground tabular">{t}</span>
          </div>
        ))}
        <div className="absolute inset-0 flex items-end gap-[3px] pr-6 sm:gap-1.5">
          {rows.map((r) => (
            <Tooltip key={r.vessel_id}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => navigate(`/vessels/${r.vessel_id}`)}
                  className="group relative flex h-full flex-1 items-end focus-visible:outline-none"
                  aria-label={`${r.vessel_name} score ${r.score}`}
                >
                  <span
                    className={cn(
                      "w-full rounded-t-[3px] opacity-85 transition-all group-hover:opacity-100 group-focus-visible:ring-2 group-focus-visible:ring-ring",
                      bandStyle[r.band].bg,
                    )}
                    style={{ height: `${Math.max(r.score, 2)}%` }}
                  />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="font-medium">{r.vessel_name} · {r.vessel_id}</p>
                <p className="text-xs opacity-80">#{r.rank} · {r.score.toFixed(1)} · {r.band}</p>
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </div>
      <div className="mt-1.5 flex gap-[3px] pr-6 sm:gap-1.5">
        {rows.map((r) => (
          <span key={r.vessel_id} className="flex-1 truncate text-center font-mono text-[9px] text-muted-foreground">
            {r.vessel_id.replace("V0", "")}
          </span>
        ))}
      </div>
    </div>
  );
}
