import { useState } from "react";
import { Link } from "react-router-dom";
import { useRecord } from "@/api/hooks";
import { RecordId } from "@/components/atoms";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/domain";
import { RecordDetailContext } from "./recordDetailContext";

const RECORD_TOKEN = /^(?:MAIN|FAIL|INS|DEF|AUD|C|V)\d+$/i;

function FieldValue({ value, currentId }: { value: string | number | null; currentId: string }) {
  if (value === null || value === "") return <span className="text-muted-foreground">—</span>;
  const text = String(value);
  if (RECORD_TOKEN.test(text) && text.toUpperCase() !== currentId.toUpperCase()) {
    return <RecordId id={text.toUpperCase()} />;
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return <span className="tabular">{formatDate(text)}</span>;
  return <span>{text}</span>;
}

export function RecordDetailProvider({ children }: { children: React.ReactNode }) {
  const [id, setId] = useState<string | null>(null);
  const record = useRecord(id);

  return (
    <RecordDetailContext.Provider value={setId}>
      {children}
      <Dialog open={id !== null} onOpenChange={(open) => !open && setId(null)}>
        <DialogContent className="sm:max-w-lg">
          {record.isLoading || !record.data ? (
            <>
              <DialogHeader>
                <DialogTitle>Record</DialogTitle>
                <DialogDescription>{record.error ? record.error.message : "Loading the record…"}</DialogDescription>
              </DialogHeader>
              {record.isLoading && <Skeleton className="h-40 w-full" />}
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle className="text-navy-900">
                  {record.data.kind} <span className="font-mono text-sm font-medium">{record.data.record_id}</span>
                </DialogTitle>
                <DialogDescription>
                  {record.data.vessel_id ? (
                    <Link
                      to={`/vessels/${record.data.vessel_id}`}
                      className="font-medium text-navy-700 underline-offset-2 hover:underline"
                      onClick={() => setId(null)}
                    >
                      {record.data.vessel_name ?? record.data.vessel_id}
                    </Link>
                  ) : (
                    "Current uploaded record"
                  )}
                </DialogDescription>
              </DialogHeader>
              <dl className="max-h-[60vh] space-y-2 overflow-y-auto">
                {record.data.fields.map((field) => (
                  <div key={field.name} className="grid grid-cols-[11rem_1fr] gap-3 border-b border-border/70 pb-2 text-sm">
                    <dt className="text-muted-foreground">{field.name}</dt>
                    <dd className="text-navy-900">
                      <FieldValue value={field.value} currentId={record.data.record_id} />
                    </dd>
                  </div>
                ))}
              </dl>
            </>
          )}
        </DialogContent>
      </Dialog>
    </RecordDetailContext.Provider>
  );
}
