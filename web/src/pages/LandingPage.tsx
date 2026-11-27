import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

type Band = "High" | "Medium" | "Low";

const bandStyle: Record<Band, { pill: string; bar: string }> = {
  High: { pill: "bg-band-high-soft text-band-high", bar: "bg-band-high" },
  Medium: { pill: "bg-band-medium-soft text-[#9a5f00]", bar: "bg-band-medium" },
  Low: { pill: "bg-band-low-soft text-band-low", bar: "bg-band-low" },
};

// Scores from the 20-vessel sample fleet, rule engine, as of 25 Nov 2026.
const preview: { name: string; score: number; band: Band; driver: string }[] = [
  { name: "MV Alpha", score: 89.4, band: "High", driver: "Detained at Hamburg · 6 open Fire Safety items" },
  { name: "MV Delta", score: 73.7, band: "High", driver: "Detained · 3+ overdue jobs on ECDIS" },
  { name: "MV Wave", score: 41.1, band: "Medium", driver: "ECDIS and Fire Pump failed 3 times" },
  { name: "MV Atlas", score: 41.1, band: "Medium", driver: "40% of maintenance overdue" },
  { name: "MV Horizon", score: 36.0, band: "Medium", driver: "7 overdue jobs on critical equipment" },
];

const components = [
  { label: "Inspection history", max: 30, owner: "Marine" },
  { label: "Deficiencies", max: 25, owner: "Marine / Technical" },
  { label: "Maintenance & equipment", max: 20, owner: "Technical" },
  { label: "Crew", max: 15, owner: "Crewing" },
  { label: "Audit / ISM", max: 10, owner: "Marine / HSQE" },
];

const bands: { label: Band; range: string }[] = [
  { label: "High", range: "60 and above · act now" },
  { label: "Medium", range: "35 to 59 · watch" },
  { label: "Low", range: "under 35 · routine" },
];

const features = [
  { num: "01", title: "Fleet ranking", text: "Every vessel ranked by risk level and score, with its top reasons and any override." },
  { num: "02", title: "Vessel report", text: "The score broken into its five parts, the biggest reasons with record IDs, and open critical issues." },
  { num: "03", title: "Evidence answers", text: "Ask about a vessel's inspections or deficiencies and get answers that cite the reports and records." },
  { num: "04", title: "Actions with owners", text: "Rule-triggered actions with an owner and due date. Closing one with evidence updates the score." },
];

const stats = [
  { value: "100%", label: "Recall · top 3", hint: "3 of 3 bad outcomes flagged" },
  { value: "67%", label: "Recall · top 2", hint: "2 of 3 bad outcomes flagged" },
  { value: "80", label: "Inspections tested", hint: "Across 20 vessels" },
  { value: "3", label: "Bad outcomes", hint: "2 detentions, 1 major deficiencies" },
];

const eyebrow = "text-xs font-semibold uppercase tracking-[0.16em]";
const h2 = "font-heading text-[clamp(30px,3.4vw,40px)] leading-[1.1] font-bold tracking-[-0.02em] text-navy-900 text-balance";
const container = "mx-auto w-full max-w-[1200px] px-6";

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b bg-white/95 backdrop-blur">
        <div className={cn(container, "flex flex-wrap items-center gap-6 py-3.5")}>
          <img src="/brand/esm-logo.png" alt="Executive Ship Management" className="block h-[34px] w-auto" />
          <nav className="ml-auto flex flex-wrap items-center gap-6 text-sm font-medium text-[#3c4b5c]">
            <a href="#how" className="hover:text-navy-900">How it works</a>
            <a href="#features" className="hover:text-navy-900">What you get</a>
            <a href="#validation" className="hover:text-navy-900">Validation</a>
            <Link
              to="/fleet"
              className="inline-flex items-center gap-1.5 rounded-lg bg-navy-700 px-4 py-2.5 text-white hover:bg-navy-900"
            >
              Open dashboard
            </Link>
          </nav>
        </div>
      </header>

      <section className="bg-gradient-to-b from-navy-900 to-navy-950 text-white">
        <div className={cn(container, "grid items-center gap-14 py-24 md:grid-cols-2")}>
          <div className="flex flex-col gap-6">
            <div className={cn(eyebrow, "text-[#9fb8d6]")}>Ship Detention Early Warning System</div>
            <h1 className="font-heading text-[clamp(40px,5.4vw,64px)] leading-[1.02] font-extrabold tracking-[-0.025em] text-balance">
              Know which ship gets detained next. Fix it before port.
            </h1>
            <p className="max-w-[52ch] text-lg text-[#c9d6e5] text-pretty">
              Every vessel in the fleet is scored 0–100 from its inspection, deficiency, maintenance, crew and audit
              records. Each score shows the records behind it, the action to take, who owns it and when it is due.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/fleet"
                className="inline-flex items-center gap-2 rounded-[9px] bg-white px-[22px] py-[13px] font-semibold text-navy-900 hover:bg-navy-50"
              >
                Open fleet ranking <ArrowRight className="size-4" />
              </Link>
              <a
                href="#how"
                className="inline-flex items-center rounded-[9px] border border-white/30 px-[22px] py-[13px] font-medium text-white hover:bg-white/10"
              >
                See how scoring works
              </a>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl bg-white text-foreground shadow-[0_30px_60px_rgba(0,0,0,.35)]">
            <div className="flex items-center justify-between gap-3 border-b border-[#eef1f5] px-[18px] py-3.5">
              <span className="font-heading text-[15px] font-bold text-navy-900">Fleet ranking</span>
              <span className="text-xs text-muted-foreground">Scored as of 25 Nov 2026</span>
            </div>
            <div className="flex flex-col">
              {preview.map((r, i) => (
                <div
                  key={r.name}
                  className="grid grid-cols-[22px_minmax(0,1fr)_88px_64px] items-center gap-3 border-b border-[#f1f3f6] px-[18px] py-3 sm:grid-cols-[22px_minmax(0,1fr)_108px_72px]"
                >
                  <span className="font-heading font-bold text-[#9aa6b4]">{i + 1}</span>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{r.name}</div>
                    <div className="truncate text-xs text-muted-foreground">{r.driver}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-[34px] font-heading text-[15px] font-bold">{r.score.toFixed(1)}</span>
                    <div className="hidden h-1.5 flex-1 rounded-full bg-[#e9edf2] sm:block">
                      <div className={cn("h-full rounded-full", bandStyle[r.band].bar)} style={{ width: `${r.score}%` }} />
                    </div>
                  </div>
                  <span className={cn("justify-self-end rounded-full px-[9px] py-0.5 text-[11px] font-semibold", bandStyle[r.band].pill)}>
                    {r.band}
                  </span>
                </div>
              ))}
            </div>
            <div className="bg-[#f7f9fb] px-[18px] py-3 text-xs text-muted-foreground">Sample view · 20 vessels scored</div>
          </div>
        </div>
      </section>

      <section id="how" className="scroll-mt-[70px]">
        <div className={cn(container, "flex flex-col gap-10 py-24")}>
          <div className="flex max-w-[720px] flex-col gap-3">
            <div className={cn(eyebrow, "text-navy-700")}>How it works</div>
            <h2 className={h2}>Five record types, one score you can explain</h2>
            <p className="text-[#3c4b5c] text-pretty">
              Each part of the score has a maximum weight and an owning team. A recent detention or a long-open Fire
              Safety deficiency puts a vessel in High whatever its score.
            </p>
          </div>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4">
            {components.map((c) => (
              <div key={c.label} className="flex flex-col gap-2.5 rounded-[14px] border bg-white p-[22px]">
                <div className="flex items-baseline justify-between">
                  <span className="font-heading text-4xl leading-none font-extrabold text-navy-900">{c.max}</span>
                  <span className="text-xs text-muted-foreground">max pts</span>
                </div>
                <div className="h-1.5 rounded-full bg-[#e9edf2]">
                  <div className="h-full rounded-full bg-navy-700" style={{ width: `${(c.max / 30) * 100}%` }} />
                </div>
                <div className="font-semibold">{c.label}</div>
                <div className="text-[13px] text-muted-foreground">Owner · {c.owner}</div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-3">
            {bands.map((b) => (
              <div key={b.label} className={cn("flex items-center gap-2.5 rounded-[10px] px-4 py-2.5 text-sm", bandStyle[b.label].pill)}>
                <strong className="font-bold">{b.label}</strong>
                <span>{b.range}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="scroll-mt-[70px] border-y bg-white">
        <div className={cn(container, "flex flex-col gap-10 py-24")}>
          <div className="flex max-w-[720px] flex-col gap-3">
            <div className={cn(eyebrow, "text-navy-700")}>What you get</div>
            <h2 className={h2}>From fleet view to a closed action</h2>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((f) => (
              <div key={f.num} className="flex flex-col gap-3 rounded-[14px] bg-background p-6">
                <span className="font-mono text-xs text-navy-700">{f.num}</span>
                <h3 className="font-heading text-xl font-bold text-navy-900">{f.title}</h3>
                <p className="text-[15px] text-[#3c4b5c] text-pretty">{f.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="validation" className="scroll-mt-[70px]">
        <div className={cn(container, "grid items-center gap-12 py-24 md:grid-cols-2")}>
          <div className="flex flex-col gap-3.5">
            <div className={cn(eyebrow, "text-navy-700")}>Validation</div>
            <h2 className={h2}>Tested against the fleet's own history</h2>
            <p className="text-[#3c4b5c] text-pretty">
              Each past inspection round was re-scored using only the records available before it. With three bad
              outcomes in 80 inspections, read this as a sanity check, not a performance claim.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {stats.map((s) => (
              <div key={s.label} className="flex flex-col gap-1.5 rounded-[14px] border bg-white p-[22px]">
                <span className="font-heading text-[44px] leading-none font-extrabold text-navy-900">{s.value}</span>
                <span className="text-sm font-semibold">{s.label}</span>
                <span className="text-[13px] text-muted-foreground">{s.hint}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 pb-24">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-6 rounded-[20px] bg-gradient-to-br from-navy-700 to-navy-900 px-[clamp(24px,5vw,64px)] py-14 text-white">
          <div className="flex max-w-[560px] flex-col gap-2">
            <h2 className="font-heading text-[clamp(26px,3vw,34px)] leading-[1.15] font-bold">See this week's High-risk vessels</h2>
            <p className="text-[#c9d6e5]">Open the ranking, then click into any vessel to see why it scored as it did.</p>
          </div>
          <Link
            to="/fleet"
            className="inline-flex items-center gap-2 rounded-[9px] bg-white px-[22px] py-[13px] font-semibold text-navy-900 hover:bg-navy-50"
          >
            Open dashboard
          </Link>
        </div>
      </section>

      <footer className="mt-auto border-t bg-white">
        <div className={cn(container, "flex flex-wrap items-center gap-4 py-6 text-[13px] text-muted-foreground")}>
          <img src="/brand/esm-logo.png" alt="Executive Ship Management" className="block h-[22px] w-auto" />
          <span className="ml-auto">Internal tool for shore staff · Scores are advisory</span>
        </div>
      </footer>
    </div>
  );
}
