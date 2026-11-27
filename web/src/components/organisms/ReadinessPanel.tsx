import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Gauge } from "lucide-react";
import type { HistoryPoint, VesselAction } from "@/api/types";
import { EmptyState, ReadinessDelta, SectionCard } from "@/components/molecules";
import { Skeleton } from "@/components/ui/skeleton";
import { BAND_THRESHOLDS, bandStyle, formatDateTime } from "@/lib/domain";
import { useScoringMode } from "@/providers/ScoringModeProvider";

interface Props {
  history?: HistoryPoint[];
  actions?: VesselAction[];
  loading?: boolean;
}

/** Section 8: how the score has moved, and what completed actions changed. */
export function ReadinessPanel({ history, actions, loading }: Props) {
  const { mode } = useScoringMode();
  const completed = (actions ?? []).filter((a) => a.status === "completed" && a.readiness);
  const data = (history ?? []).map((h, i) => ({ ...h, idx: i + 1, label: formatDateTime(h.created_at) }));

  return (
    <SectionCard
      id="readiness"
      number={8}
      title="Readiness"
      icon={Gauge}
      subtitle={
        mode === "model"
          ? "Rule score after each upload or completed action. The model score is the number in the header."
          : "Score after each recalculation, and the effect of completed actions"
      }
    >
      {loading ? (
        <Skeleton className="h-56 w-full" />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ left: -16, right: 12, top: 8, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="idx" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                <ReferenceLine y={BAND_THRESHOLDS.high} stroke={bandStyle.High.hex} strokeDasharray="4 4" strokeOpacity={0.6} />
                <ReferenceLine y={BAND_THRESHOLDS.medium} stroke={bandStyle.Medium.hex} strokeDasharray="4 4" strokeOpacity={0.6} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid var(--border)", fontSize: 12 }}
                  labelFormatter={(_, p) => (p?.[0] ? `${p[0].payload.label} · ${p[0].payload.trigger}` : "")}
                  formatter={(v, _n, item) => [`${Number(v).toFixed(1)} (${item.payload.band})`, "Score"]}
                />
                <Line
                  type="stepAfter"
                  dataKey="score"
                  stroke="var(--navy-700)"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "white", stroke: "var(--navy-700)", strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2">
            <p className="text-eyebrow text-muted-foreground">Completed actions</p>
            {completed.length ? (
              <ul className="space-y-2">
                {completed.map((a) => (
                  <li key={a.id} className="rounded-lg border bg-muted/30 p-3">
                    <p className="line-clamp-2 text-xs font-medium text-foreground">{a.text}</p>
                    <ReadinessDelta readiness={a.readiness!} className="mt-2" />
                    <p className="mt-1.5 text-[11px] text-muted-foreground">
                      {a.completed_by} · {formatDateTime(a.completed_at)}
                      {a.completion_evidence && <> · “{a.completion_evidence}”</>}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No actions completed yet" description="Complete an action above to see its effect on the score." className="py-6" />
            )}
          </div>
        </div>
      )}
    </SectionCard>
  );
}
