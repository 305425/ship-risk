import { Link } from "react-router-dom";
import { ArrowLeft, Clock, ShieldAlert } from "lucide-react";
import type { VesselRisk } from "@/api/types";
import { BandBadge, ConfidenceMeter, Eyebrow, RecordId } from "@/components/atoms";
import { RiskGauge } from "@/components/molecules";
import { bandStyle, formatDate, formatDateTime } from "@/lib/domain";
import { useScoringMode } from "@/providers/ScoringModeProvider";

/** Section 1 of the vessel report: the current risk at a glance. */
export function VesselHero({ risk, rank, fleetSize }: { risk: VesselRisk; rank?: number; fleetSize?: number }) {
  const { mode } = useScoringMode();
  const overridden = mode === "rules" && risk.overrides.length > 0;
  return (
    <section id="current-risk" className="relative scroll-mt-24 overflow-hidden rounded-2xl bg-bridge text-white shadow-xl shadow-navy-900/15">
      <div className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] [background-size:28px_28px]" />
      <div className="absolute inset-x-0 top-0 h-1 bg-silver" />
      <div className="relative grid gap-6 p-6 md:grid-cols-[1fr_auto] md:p-8">
        <div className="space-y-5">
          <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-white/60 hover:text-white">
            <ArrowLeft className="size-3.5" /> Fleet ranking
          </Link>
          <div className="space-y-2">
            <Eyebrow className="text-white/50">01 · Current risk</Eyebrow>
            <h1 className="font-display text-3xl font-bold tracking-tight md:text-4xl">{risk.vessel_name ?? risk.vessel_id}</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm text-white/70">
              <span className="font-mono">{risk.vessel_id}</span>
              {rank && fleetSize && (
                <>
                  <span className="text-white/30">•</span>
                  <span>Rank <strong className="text-white">#{rank}</strong> of {fleetSize}</span>
                </>
              )}
              <span className="text-white/30">•</span>
              <span className="inline-flex items-center gap-1"><Clock className="size-3.5" /> Scored {formatDate(risk.as_of)}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <BandBadge band={risk.band} size="lg" showHint className="bg-white ring-0" />
            <span className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-1.5 text-sm">
              <span className="text-white/60">Confidence</span>
              <ConfidenceMeter value={risk.confidence} className="text-white [&_span.bg-silver-200]:bg-white/25 [&_span.bg-navy-700]:bg-white" />
            </span>
          </div>

          {overridden && (
            <div className="space-y-2 rounded-lg border border-white/10 bg-white/[0.06] p-3.5">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider" style={{ color: "#ff9b90" }}>
                <ShieldAlert className="size-4" /> Overrides forcing High
              </p>
              <ul className="space-y-1.5">
                {risk.overrides.map((o) => (
                  <li key={o.id + o.text} className="flex flex-wrap items-center gap-2 text-sm text-white/90">
                    <span className="size-1.5 rounded-full" style={{ background: bandStyle.High.hex }} />
                    {o.text}
                    <span className="flex flex-wrap gap-1">
                      {o.record_ids.slice(0, 4).map((id) => (
                        <RecordId key={id} id={id} className="border-white/15 bg-white/10 text-white/85" />
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {risk.confidence_reasons.length > 0 && (
            <p className="text-xs text-white/55">
              Confidence is {risk.confidence.toLowerCase()} because: {risk.confidence_reasons.map((c) => c.text).join("; ")}.
            </p>
          )}
        </div>

        <div className="flex flex-col items-center justify-center gap-3 self-start rounded-xl bg-white px-6 pt-5 pb-4 text-foreground shadow-inner md:w-72">
          <Eyebrow>Risk score</Eyebrow>
          <RiskGauge score={risk.score} band={risk.band} overridden={overridden} />
          <p className="text-center text-[11px] text-muted-foreground">
            {mode === "model"
              ? "Registered model score. High starts at 60 and Medium at 35."
              : `Last recalculated ${formatDateTime(risk.created_at)} after ${risk.trigger === "action" ? "an action was completed" : "a data upload"}`}
          </p>
        </div>
      </div>
    </section>
  );
}
