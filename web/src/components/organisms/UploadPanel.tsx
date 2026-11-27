import { useState } from "react";
import { CheckCircle2, FileSpreadsheet, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/api/client";
import { useUpload } from "@/api/hooks";
import type { UploadResult } from "@/api/types";
import { FileDropzone, SectionCard } from "@/components/molecules";
import { Button } from "@/components/ui/button";
import { EXPECTED_FILES, TABLE_LABELS } from "@/lib/domain";
import { cn } from "@/lib/utils";
import { RankingChanges } from "./RankingChanges";
import { ValidationErrors } from "./ValidationErrors";

function knownFile(name: string) {
  const stem = name.replace(/\.csv$/i, "").replace(/[_\s]/g, "").toLowerCase();
  return Object.entries(TABLE_LABELS).some(([table, label]) => stem === label.toLowerCase() || stem === table.replace("_", ""));
}

function UploadSummary({ result }: { result: UploadResult }) {
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3 rounded-lg border border-band-low/25 bg-band-low-soft p-4">
        <CheckCircle2 className="mt-0.5 size-5 text-band-low" />
        <div className="text-sm">
          <p className="font-semibold text-foreground">Upload saved and fleet recalculated</p>
          <p className="text-muted-foreground">
            Actions: {result.actions.created ?? 0} created, {result.actions.updated ?? 0} updated, {result.actions.superseded ?? 0} superseded.
            Evidence indexing {result.indexing === "scheduled" ? "is running in the background" : "is disabled (no LLM key)"}.
          </p>
        </div>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-eyebrow text-muted-foreground">Files</p>
          <ul className="divide-y rounded-lg border">
            {result.files.map((f) => (
              <li key={f.upload_id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                <span className="flex items-center gap-2 font-medium">
                  <FileSpreadsheet className="size-4 text-navy-700" />
                  {f.file_name}
                </span>
                <span className="flex gap-3 text-xs tabular">
                  <span className="text-muted-foreground">{f.row_count} rows</span>
                  <span className="text-band-low">+{f.rows_added}</span>
                  <span className="text-band-medium">~{f.rows_changed}</span>
                  <span className="text-band-high">−{f.rows_removed}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-2">
          <p className="text-eyebrow text-muted-foreground">Ranking changes</p>
          <RankingChanges changes={result.ranking_changes} />
        </div>
      </div>
    </div>
  );
}

export function UploadPanel() {
  const upload = useUpload();
  const [files, setFiles] = useState<File[]>([]);

  const add = (incoming: File[]) => {
    upload.reset();
    setFiles((prev) => {
      const byName = new Map(prev.map((f) => [f.name, f]));
      incoming.forEach((f) => byName.set(f.name, f));
      return [...byName.values()];
    });
  };

  const submit = () =>
    upload.mutate(files, {
      onSuccess: (res) => {
        setFiles([]);
        toast.success(`${res.files.length} file${res.files.length === 1 ? "" : "s"} uploaded`, {
          description: `${res.ranking_changes.length} vessel score${res.ranking_changes.length === 1 ? "" : "s"} changed`,
        });
      },
    });

  const rowErrors = upload.error instanceof ApiError ? upload.error.rowErrors : [];

  return (
    <SectionCard title="Upload CSV data" subtitle="Validated as one batch: if any row fails, nothing is saved">
      <div className="space-y-5">
        <FileDropzone onFiles={add} disabled={upload.isPending} />

        {files.length > 0 && (
          <div className="space-y-3">
            <ul className="grid gap-2 sm:grid-cols-2">
              {files.map((f) => {
                const ok = knownFile(f.name);
                return (
                  <li key={f.name} className={cn("flex items-center gap-3 rounded-lg border px-3 py-2", !ok && "border-band-medium/40 bg-band-medium-soft")}>
                    <FileSpreadsheet className={cn("size-4", ok ? "text-navy-700" : "text-band-medium")} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{f.name}</p>
                      <p className="text-[11px] text-muted-foreground">{ok ? `${(f.size / 1024).toFixed(1)} KB` : "Unrecognised name, will be rejected"}</p>
                    </div>
                    <Button variant="ghost" size="icon" className="size-7" onClick={() => setFiles((p) => p.filter((x) => x !== f))} aria-label={`Remove ${f.name}`}>
                      <X className="size-4" />
                    </Button>
                  </li>
                );
              })}
            </ul>
            <div className="flex items-center justify-end gap-2">
              <Button variant="outline" onClick={() => setFiles([])} disabled={upload.isPending}>Clear</Button>
              <Button onClick={submit} disabled={upload.isPending}>
                {upload.isPending && <Loader2 className="size-4 animate-spin" />}
                Validate and upload {files.length} file{files.length === 1 ? "" : "s"}
              </Button>
            </div>
          </div>
        )}

        {upload.error && (rowErrors.length ? <ValidationErrors errors={rowErrors} /> : <p className="text-sm text-destructive">{upload.error.message}</p>)}
        {upload.data && <UploadSummary result={upload.data} />}

        <p className="text-xs text-muted-foreground">
          Expected file names: {EXPECTED_FILES.join(", ")}.
        </p>
      </div>
    </SectionCard>
  );
}
