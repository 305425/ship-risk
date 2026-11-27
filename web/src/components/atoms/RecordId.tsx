import { useRecordDetail } from "@/providers/recordDetailContext";
import { cn } from "@/lib/utils";

export function RecordId({ id, className }: { id: string; className?: string }) {
  const openRecord = useRecordDetail();
  return (
    <button
      type="button"
      title={`Show ${id}`}
      onClick={(event) => {
        event.stopPropagation();
        openRecord(id);
      }}
      className={cn(
        "inline-flex h-5 cursor-pointer items-center rounded border border-navy-100 bg-navy-50 px-1.5 font-mono text-[11px] font-medium text-navy-800 underline-offset-2 hover:underline",
        className,
      )}
    >
      {id}
    </button>
  );
}
