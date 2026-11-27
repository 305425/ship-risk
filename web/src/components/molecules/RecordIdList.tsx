import { RecordId } from "@/components/atoms";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export function RecordIdList({ ids, max = 4 }: { ids: string[]; max?: number }) {
  if (!ids.length) return null;
  const shown = ids.slice(0, max);
  const rest = ids.slice(max);
  return (
    <div className="flex flex-wrap items-center gap-1">
      {shown.map((id) => (
        <RecordId key={id} id={id} />
      ))}
      {rest.length > 0 && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" className="h-5 rounded px-1.5 text-[11px] font-medium text-navy-700 hover:bg-navy-50">
              +{rest.length} more
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">
            <span className="flex flex-wrap gap-1">
              {rest.map((id) => (
                <RecordId key={id} id={id} />
              ))}
            </span>
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}
