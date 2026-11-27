import { Link } from "react-router-dom";
import type { RankingChange } from "@/api/types";
import { EmptyState, ReadinessDelta } from "@/components/molecules";
import { BandBadge } from "@/components/atoms";

export function RankingChanges({ changes }: { changes: RankingChange[] }) {
  if (!changes.length) return <EmptyState title="No score changes" description="This upload didn't move any vessel's score or band." className="py-6" />;
  const sorted = [...changes].sort(
    (a, b) => Math.abs(b.after.score - (b.before?.score ?? 0)) - Math.abs(a.after.score - (a.before?.score ?? 0)),
  );
  return (
    <ul className="divide-y rounded-lg border">
      {sorted.map((c) => (
        <li key={c.vessel_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
          <Link to={`/vessels/${c.vessel_id}`} className="font-mono text-sm font-medium text-navy-700 hover:underline">
            {c.vessel_id}
          </Link>
          {c.before ? (
            <ReadinessDelta readiness={{ before: c.before, after: c.after, text: "" }} />
          ) : (
            <span className="flex items-center gap-2 text-xs text-muted-foreground">
              New <BandBadge band={c.after.band} size="sm" /> <span className="font-heading font-semibold tabular text-foreground">{c.after.score.toFixed(0)}</span>
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
