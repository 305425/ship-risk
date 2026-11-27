import type { Band } from "@/api/types";
import { BAND_THRESHOLDS, bandStyle } from "@/lib/domain";
import { cn } from "@/lib/utils";

const CX = 100;
const CY = 100;
const R = 80;

function point(score: number, radius = R) {
  const angle = Math.PI * (1 - score / 100);
  return { x: CX + radius * Math.cos(angle), y: CY - radius * Math.sin(angle) };
}

function arc(from: number, to: number) {
  const a = point(from);
  const b = point(to);
  return `M ${a.x} ${a.y} A ${R} ${R} 0 0 1 ${b.x} ${b.y}`;
}

interface RiskGaugeProps {
  score: number;
  band: Band;
  overridden?: boolean;
  className?: string;
}

/** Semicircular instrument dial; zone boundaries follow the band thresholds in rules.yaml. */
export function RiskGauge({ score, band, overridden, className }: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const needle = point(clamped, R - 18);
  const ticks = Array.from({ length: 11 }, (_, i) => i * 10);

  return (
    <div className={cn("flex w-full max-w-[240px] flex-col items-center", className)}>
      <svg viewBox="0 0 200 116" className="w-full overflow-visible">
        <path d={arc(0, 100)} fill="none" stroke="var(--silver-100)" strokeWidth="14" strokeLinecap="butt" />
        <path d={arc(0, BAND_THRESHOLDS.medium)} fill="none" stroke={bandStyle.Low.hex} strokeOpacity="0.85" strokeWidth="14" />
        <path
          d={arc(BAND_THRESHOLDS.medium, BAND_THRESHOLDS.high)}
          fill="none"
          stroke={bandStyle.Medium.hex}
          strokeOpacity="0.85"
          strokeWidth="14"
        />
        <path d={arc(BAND_THRESHOLDS.high, 100)} fill="none" stroke={bandStyle.High.hex} strokeOpacity="0.85" strokeWidth="14" />
        {ticks.map((t) => {
          const outer = point(t, R - 10);
          const inner = point(t, R - (t % 50 === 0 ? 20 : 15));
          return (
            <line key={t} x1={outer.x} y1={outer.y} x2={inner.x} y2={inner.y} stroke="var(--navy-800)" strokeOpacity="0.35" strokeWidth="1" />
          );
        })}
        <line
          x1={CX}
          y1={CY}
          x2={needle.x}
          y2={needle.y}
          stroke="var(--navy-900)"
          strokeWidth="3"
          strokeLinecap="round"
          className="origin-[100px_100px] transition-all duration-700"
        />
        <circle cx={CX} cy={CY} r="7" fill="var(--navy-900)" />
        <circle cx={CX} cy={CY} r="2.5" fill="var(--silver-200)" />
        <text x={point(0, R + 4).x - 4} y={CY + 14} fontSize="8" fill="var(--muted-foreground)">0</text>
        <text x={point(100, R + 4).x - 6} y={CY + 14} fontSize="8" fill="var(--muted-foreground)">100</text>
      </svg>
      <span className={cn("mt-1 font-display text-4xl leading-none font-bold tabular", bandStyle[band].text)}>
        {clamped.toFixed(1)}
      </span>
      <span className="mt-1 text-[11px] text-muted-foreground">out of 100</span>
      {overridden && (
        <span className="mt-2 rounded bg-band-high-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-band-high">
          Override applied
        </span>
      )}
    </div>
  );
}
