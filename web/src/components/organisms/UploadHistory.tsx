import { useState } from "react";
import { History } from "lucide-react";
import { useUploadDiff, useUploads } from "@/api/hooks";
import { RecordId } from "@/components/atoms";
import { EmptyState, ErrorState, SectionCard } from "@/components/molecules";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, TABLE_LABELS } from "@/lib/domain";
import { RankingChanges } from "./RankingChanges";

function DiffSheet({ uploadId, onClose }: { uploadId: number | null; onClose: () => void }) {
  const { data, isLoading, error } = useUploadDiff(uploadId);
  return (
    <Sheet open={uploadId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="font-heading text-navy-900">
            {data ? `${TABLE_LABELS[data.upload.table_name]} · upload #${data.upload.id}` : "Upload diff"}
          </SheetTitle>
          <SheetDescription>
            {data?.previous_upload_id ? `Compared with upload #${data.previous_upload_id}` : "First version of this table"}
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-6 px-4 pb-8">
          {isLoading && <Skeleton className="h-40 w-full" />}
          {error && <ErrorState error={error} />}
          {data && (
            <>
              <div className="grid grid-cols-3 gap-2 text-center">
                {[
                  { label: "Added", n: data.added.length, cls: "text-band-low" },
                  { label: "Changed", n: data.changed.length, cls: "text-band-medium" },
                  { label: "Removed", n: data.removed.length, cls: "text-band-high" },
                ].map((s) => (
                  <div key={s.label} className="rounded-lg border p-3">
                    <p className={`font-display text-2xl font-bold tabular ${s.cls}`}>{s.n}</p>
                    <p className="text-eyebrow text-muted-foreground">{s.label}</p>
                  </div>
                ))}
              </div>
              {data.changed.length > 0 && (
                <div className="space-y-2">
                  <p className="text-eyebrow text-muted-foreground">Changed rows</p>
                  <ul className="space-y-2">
                    {data.changed.slice(0, 50).map((c) => (
                      <li key={c.key} className="rounded-lg border p-3">
                        <RecordId id={c.key} />
                        <ul className="mt-2 space-y-1">
                          {Object.entries(c.fields).map(([field, v]) => (
                            <li key={field} className="grid grid-cols-[10rem_1fr] gap-2 text-xs">
                              <span className="font-mono text-muted-foreground">{field}</span>
                              <span>
                                <span className="text-band-high line-through">{v.old || "∅"}</span>{" "}
                                <span className="text-band-low">{v.new || "∅"}</span>
                              </span>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(data.added.length > 0 || data.removed.length > 0) && data.previous_upload_id && (
                <div className="space-y-2 text-xs">
                  {data.added.length > 0 && (
                    <p className="flex flex-wrap items-center gap-1">
                      <span className="font-semibold text-band-low">Added:</span>
                      {data.added.slice(0, 40).map((id) => <RecordId key={id} id={id} />)}
                    </p>
                  )}
                  {data.removed.length > 0 && (
                    <p className="flex flex-wrap items-center gap-1">
                      <span className="font-semibold text-band-high">Removed:</span>
                      {data.removed.slice(0, 40).map((id) => <RecordId key={id} id={id} />)}
                    </p>
                  )}
                </div>
              )}
              <div className="space-y-2">
                <p className="text-eyebrow text-muted-foreground">Ranking changes from this batch</p>
                <RankingChanges changes={data.ranking_changes} />
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function UploadHistory() {
  const { data, isLoading, error, refetch } = useUploads();
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <SectionCard title="Upload history" icon={History} subtitle="Every file is kept as a version. Select a row to see what changed." bodyClassName="p-0">
      {isLoading ? (
        <div className="p-5"><Skeleton className="h-48 w-full" /></div>
      ) : error ? (
        <div className="p-5"><ErrorState error={error} onRetry={refetch} /></div>
      ) : !data?.length ? (
        <div className="p-5"><EmptyState title="No uploads yet" description="Upload the 8 sample CSVs to start scoring." /></div>
      ) : (
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">#</TableHead>
              <TableHead>Table</TableHead>
              <TableHead>File</TableHead>
              <TableHead className="text-right">Rows</TableHead>
              <TableHead className="text-right">Δ</TableHead>
              <TableHead>By</TableHead>
              <TableHead>When</TableHead>
              <TableHead className="pr-5">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((u) => (
              <TableRow key={u.id} className="cursor-pointer" onClick={() => setSelected(u.id)}>
                <TableCell className="pl-5 font-mono text-xs text-muted-foreground">{u.id}</TableCell>
                <TableCell className="font-medium">{TABLE_LABELS[u.table_name] ?? u.table_name}</TableCell>
                <TableCell className="max-w-48 truncate text-muted-foreground">{u.file_name}</TableCell>
                <TableCell className="text-right tabular">{u.row_count}</TableCell>
                <TableCell className="text-right text-xs tabular">
                  <span className="text-band-low">+{u.rows_added}</span>{" "}
                  <span className="text-band-medium">~{u.rows_changed}</span>{" "}
                  <span className="text-band-high">−{u.rows_removed}</span>
                </TableCell>
                <TableCell className="text-muted-foreground">{u.uploaded_by}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{formatDateTime(u.created_at)}</TableCell>
                <TableCell className="pr-5">
                  <Badge variant={u.status === "loaded" || u.status === "indexed" ? "secondary" : "outline"} className="capitalize">
                    {u.status.replace("_", " ")}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <DiffSheet uploadId={selected} onClose={() => setSelected(null)} />
    </SectionCard>
  );
}
