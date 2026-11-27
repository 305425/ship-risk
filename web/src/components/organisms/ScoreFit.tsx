import { useNavigate } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ShadowModelReport } from "@/api/types";
import { SectionCard } from "@/components/molecules";
import { BAND_THRESHOLDS } from "@/lib/domain";
import { bandForScore } from "@/lib/scoringMode";

const RULES_COLOR = "#174a7c";
const MODEL_COLOR = "#e07a12";

type Point = ShadowModelReport["current"][number] & {
  model_band: ReturnType<typeof bandForScore>;
  gap: number;
};

function FitTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-lg border bg-card px-3 py-2 text-xs shadow-sm">
      <p className="font-medium text-navy-900">{row.vessel_name}</p>
      <p className="font-mono text-[11px] text-muted-foreground">{row.vessel_id}</p>
      <p className="mt-1.5">
        <span className="font-semibold" style={{ color: RULES_COLOR }}>Rules</span>{" "}
        <span className="font-heading tabular">{row.rule_score.toFixed(1)}</span> · {row.rule_band}
      </p>
      <p>
        <span className="font-semibold" style={{ color: MODEL_COLOR }}>Model</span>{" "}
        <span className="font-heading tabular">{row.shadow_score.toFixed(1)}</span> · {row.model_band}
      </p>
      <p className="mt-1 text-muted-foreground">Gap {row.gap.toFixed(1)}</p>
    </div>
  );
}

/** Both scores on one 0–100 axis, vessels ordered by the rule score so agreement is a shared slope. */
export function ScoreFitChart({ rows }: { rows: ShadowModelReport["current"] }) {
  const navigate = useNavigate();
  const points: Point[] = [...rows]
    .sort((a, b) => b.rule_score - a.rule_score || a.vessel_id.localeCompare(b.vessel_id))
    .map((row) => ({
      ...row,
      model_band: bandForScore(row.shadow_score),
      gap: Math.abs(row.shadow_score - row.rule_score),
    }));
  const sameBand = points.filter((row) => row.model_band === row.rule_band).length;
  const meanGap = points.length ? points.reduce((sum, row) => sum + row.gap, 0) / points.length : 0;
  const widest = points.reduce<Point | null>((best, row) => (best === null || row.gap > best.gap ? row : best), null);

  return (
    <SectionCard
      title="Rules and model together"
      subtitle="Vessels ordered by the rule score, highest first. The lines sit together where both approaches agree."
    >
      <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
        <span>
          Same band <span className="font-heading font-semibold tabular text-navy-900">{sameBand}</span> of {points.length}
        </span>
        <span>
          Average gap <span className="font-heading font-semibold tabular text-navy-900">{meanGap.toFixed(1)}</span>
        </span>
        {widest && (
          <span>
            Widest gap <span className="font-medium text-navy-900">{widest.vessel_name}</span>
            {" "}
            <span className="font-heading tabular">{widest.gap.toFixed(1)}</span>
          </span>
        )}
      </div>
      <div className="mb-2 flex flex-wrap gap-5 text-sm font-medium text-navy-900">
        <span className="inline-flex items-center gap-2">
          <span className="h-1.5 w-8 rounded-full" style={{ backgroundColor: RULES_COLOR }} />
          Rules
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-1.5 w-8 rounded-full" style={{ backgroundColor: MODEL_COLOR }} />
          Model
        </span>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={points}
            margin={{ left: -8, right: 12, top: 8, bottom: 0 }}
            onClick={(state) => {
              const id = typeof state?.activeLabel === "string" ? state.activeLabel : undefined;
              if (id) navigate(`/vessels/${id}`);
            }}
          >
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="vessel_id"
              interval={Math.max(0, Math.ceil(points.length / 12) - 1)}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
            <ReferenceLine y={BAND_THRESHOLDS.high} stroke="var(--band-high)" strokeDasharray="4 4" strokeOpacity={0.55} />
            <ReferenceLine y={BAND_THRESHOLDS.medium} stroke="var(--band-medium)" strokeDasharray="4 4" strokeOpacity={0.55} />
            <Tooltip content={<FitTooltip />} />
            <Line
              type="linear"
              dataKey="rule_score"
              name="Rules"
              stroke={RULES_COLOR}
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 5, fill: RULES_COLOR }}
            />
            <Line
              type="linear"
              dataKey="shadow_score"
              name="Model"
              stroke={MODEL_COLOR}
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 5, fill: MODEL_COLOR }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
        Dashed lines are High at {BAND_THRESHOLDS.high} and Medium at {BAND_THRESHOLDS.medium}. The rules also count maintenance, crew and audit records.
        The model uses inspection and deficiency history only, so the lines separate when those other records move a vessel. Click a point to open that vessel.
      </p>
    </SectionCard>
  );
}
