import { useState, type ReactNode } from "react";
import { BookOpenText, FileText, Loader2, Sparkles, Table2, TriangleAlert } from "lucide-react";
import { ApiError, signInFleetChat } from "@/api/client";
import { useEvidence, useIndexStatus } from "@/api/hooks";
import type { Citation, EvidenceQuery } from "@/api/types";
import { RecordId } from "@/components/atoms";
import { EmptyState, SectionCard } from "@/components/molecules";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { formatDate } from "@/lib/domain";
import { useRecordDetail } from "@/providers/recordDetailContext";

const SUGGESTIONS = [
  "Why was this vessel detained or given major findings?",
  "What fire safety problems are still open?",
  "Which critical equipment has repeated failures?",
];

const INLINE = /\*\*([^*]+)\*\*|\[(\d+)\]|\b((?:MAIN|FAIL|INS|DEF|AUD)\d+|(?:C|V)\d{3,})\b/g;

function InlineText({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  const pattern = new RegExp(INLINE.source, "g");
  let last = 0;
  let key = 0;
  for (let match = pattern.exec(text); match; match = pattern.exec(text)) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[1]) {
      parts.push(
        <strong key={key} className="font-semibold text-navy-900">
          <InlineText text={match[1]} />
        </strong>,
      );
    } else if (match[2]) {
      const n = match[2];
      parts.push(
        <button
          key={key}
          type="button"
          title={`Source ${n}`}
          onClick={() => document.getElementById(`evidence-cite-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" })}
          className="mx-0.5 inline-flex size-4 items-center justify-center rounded bg-navy-900 align-text-top font-heading text-[10px] font-bold text-white"
        >
          {n}
        </button>,
      );
    } else if (match[3]) {
      parts.push(<RecordId key={key} id={match[3]} className="mx-0.5 align-text-bottom" />);
    }
    key += 1;
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

function EvidenceAnswer({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let items: string[] = [];
  let key = 0;
  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(
      <p key={key} className="text-sm leading-relaxed text-foreground">
        <InlineText text={paragraph.join(" ")} />
      </p>,
    );
    key += 1;
    paragraph = [];
  };
  const flushList = () => {
    if (!items.length) return;
    blocks.push(
      <ul key={key} className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-foreground">
        {items.map((item, index) => (
          <li key={`${index}-${item.slice(0, 24)}`}>
            <InlineText text={item} />
          </li>
        ))}
      </ul>,
    );
    key += 1;
    items = [];
  };
  for (const line of lines) {
    const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
    if (bullet) {
      flushParagraph();
      items.push(bullet[1]);
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    flushList();
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();
  return <div className="space-y-2">{blocks}</div>;
}

function CitationCard({ c }: { c: Citation }) {
  const openRecord = useRecordDetail();
  const Icon = c.source_type === "report" ? FileText : Table2;
  const evidenceId = c.evidence_id || c.record_id;
  return (
    <li id={c.index ? `evidence-cite-${c.index}` : undefined} className="rounded-lg border bg-muted/30 p-3">
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <span className="flex size-5 items-center justify-center rounded bg-navy-900 font-heading text-[10px] font-bold text-white">{c.index}</span>
        <Icon className="size-3.5 text-navy-700" />
        {evidenceId ? (
          <button
            type="button"
            className="text-xs font-medium text-foreground underline-offset-2 hover:underline"
            onClick={() => openRecord(evidenceId)}
          >
            {c.label ?? c.evidence_id}
          </button>
        ) : (
          <span className="text-xs font-medium text-foreground">{c.label ?? c.evidence_id}</span>
        )}
        {c.record_id && <RecordId id={c.record_id} />}
        {c.date && <span className="text-[11px] text-muted-foreground">{formatDate(c.date)}</span>}
        {c.status && <Badge variant="outline" className="h-4 text-[10px] capitalize">{c.status}</Badge>}
        {c.synthetic && <Badge variant="secondary" className="h-4 text-[10px]">Synthetic report</Badge>}
      </div>
      <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">{c.snippet}</p>
    </li>
  );
}

/** Section 3: cited evidence from the vessel's own records and inspection reports. */
export function EvidencePanel({ vesselId }: { vesselId: string }) {
  const status = useIndexStatus();
  const evidence = useEvidence(vesselId);
  const [q, setQ] = useState("");
  const [source, setSource] = useState<"all" | "record" | "report">("all");
  const [onlyOpen, setOnlyOpen] = useState(false);

  const disabledReason =
    status.data && !status.data.enabled
      ? status.data.reason
      : evidence.error instanceof ApiError && evidence.error.status === 503
        ? evidence.error.message
        : null;

  const ask = (question: string) => {
    if (question.trim().length < 3) return;
    setQ(question);
    const params: EvidenceQuery = { q: question.trim() };
    if (source !== "all") params.source_type = source;
    if (onlyOpen) params.status = "open";
    evidence.mutate(params);
  };

  return (
    <SectionCard
      id="evidence"
      number={3}
      title="Evidence"
      icon={BookOpenText}
      subtitle="Ask about this vessel. Answers cite its records and inspection reports only."
    >
      <a
        href="/chat/"
        className="text-xs font-medium text-navy-700 underline-offset-2 hover:underline"
        onClick={async (event) => {
          event.preventDefault();
          await signInFleetChat();
          window.location.assign("/chat/");
        }}
      >
        Open the fleet assistant
      </a>
      {disabledReason ? (
        <EmptyState
          icon={Sparkles}
          title="Evidence search is switched off"
          description={`${disabledReason}. Scores, drivers, issues and actions still work; the records behind them are listed under Critical issues.`}
        />
      ) : (
        <div className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask(q);
            }}
            className="space-y-2"
          >
            <Textarea
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. What did the last PSC inspection find?"
              rows={2}
              maxLength={500}
              className="resize-none bg-card"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  ask(q);
                }
              }}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Select value={source} onValueChange={(v) => setSource(v as typeof source)}>
                <SelectTrigger size="sm" className="w-40 bg-card">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All sources</SelectItem>
                  <SelectItem value="record">Data records</SelectItem>
                  <SelectItem value="report">Inspection reports</SelectItem>
                </SelectContent>
              </Select>
              <Button type="button" size="sm" variant={onlyOpen ? "secondary" : "outline"} onClick={() => setOnlyOpen((v) => !v)}>
                {onlyOpen ? "✓ " : ""}Open items only
              </Button>
              <Button type="submit" size="sm" className="ml-auto" disabled={evidence.isPending || q.trim().length < 3}>
                {evidence.isPending ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                Ask
              </Button>
            </div>
          </form>

          {!evidence.data && !evidence.isPending && (
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => ask(s)}
                  className="rounded-full border bg-card px-3 py-1 text-xs text-navy-800 transition-colors hover:border-navy-600/50 hover:bg-navy-50"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {evidence.error && !(evidence.error instanceof ApiError && evidence.error.status === 503) && (
            <p className="flex items-center gap-2 text-sm text-destructive">
              <TriangleAlert className="size-4" /> {evidence.error.message}
            </p>
          )}

          {evidence.data && (
            <div className="space-y-3 rounded-lg border border-navy-100 bg-navy-50/40 p-4">
              {evidence.data.refused ? (
                <p className="text-sm text-muted-foreground">{evidence.data.answer}</p>
              ) : (
                <>
                  <EvidenceAnswer text={evidence.data.answer} />
                  <ul className="grid gap-2 md:grid-cols-2">
                    {evidence.data.citations.map((c) => (
                      <CitationCard key={`${c.index}-${c.evidence_id}`} c={c} />
                    ))}
                  </ul>
                  <p className="text-[11px] text-muted-foreground">
                    {evidence.data.retrieved} passages retrieved · evidence coverage {Math.round(evidence.data.evidence_coverage * 100)}% · {evidence.data.model}
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}
