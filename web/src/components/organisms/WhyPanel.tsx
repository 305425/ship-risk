import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Lightbulb } from "lucide-react";
import type { VesselRisk } from "@/api/types";
import { DriverItem, SectionCard } from "@/components/molecules";
import { COMPONENTS } from "@/lib/domain";
import { useScoringMode } from "@/providers/ScoringModeProvider";

function BreakdownChart({ risk }: { risk: VesselRisk }) {
  const data = COMPONENTS.map(({ key, short }) => {
    const c = risk.components[key];
    return { name: short, points: c?.points ?? 0, headroom: Math.max(0, (c?.max_points ?? 0) - (c?.points ?? 0)), max: c?.max_points ?? 0 };
  });
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }} barCategoryGap={10}>
          <CartesianGrid horizontal={false} stroke="var(--border)" />
          <XAxis type="number" domain={[0, 30]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" width={92} tick={{ fontSize: 12, fill: "var(--foreground)" }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: "var(--navy-50)" }}
            contentStyle={{ borderRadius: 8, border: "1px solid var(--border)", fontSize: 12 }}
            formatter={(value, name, item) =>
              name === "points" ? [`${Number(value).toFixed(1)} of ${item.payload.max}`, "Points"] : [null, null]
            }
          />
          <Bar dataKey="points" stackId="a" fill="var(--navy-700)" radius={[0, 0, 0, 0]} />
          <Bar dataKey="headroom" stackId="a" fill="var(--silver-100)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Section 2: why the vessel scores what it does. */
export function WhyPanel({ risk }: { risk: VesselRisk }) {
  const { mode } = useScoringMode();
  return (
    <SectionCard
      id="why"
      number={2}
      title="Why"
      icon={Lightbulb}
      subtitle={
        mode === "model"
          ? "These points are the rule breakdown. The score above comes from the model."
          : "Score breakdown by component and the three biggest drivers"
      }
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div>
          <p className="mb-2 text-xs text-muted-foreground">Points earned (navy) against each component's maximum weight</p>
          <BreakdownChart risk={risk} />
        </div>
        <div className="divide-y">
          {risk.drivers.length ? (
            risk.drivers.map((d, i) => <DriverItem key={d.feature} driver={d} index={i} />)
          ) : (
            <p className="py-3 text-sm text-muted-foreground">No component is contributing points.</p>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
