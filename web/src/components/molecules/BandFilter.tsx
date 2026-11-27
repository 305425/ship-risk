import type { Band } from "@/api/types";
import { Pennant } from "@/components/atoms";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { BANDS, bandStyle } from "@/lib/domain";

export type BandFilterValue = Band | "All";

interface BandFilterProps {
  value: BandFilterValue;
  onChange: (value: BandFilterValue) => void;
  counts: Record<Band, number>;
  total: number;
}

export function BandFilter({ value, onChange, counts, total }: BandFilterProps) {
  return (
    <ToggleGroup
      type="single"
      variant="outline"
      size="sm"
      value={value}
      onValueChange={(v) => onChange((v || "All") as BandFilterValue)}
      className="bg-card"
    >
      <ToggleGroupItem value="All" className="gap-1.5 px-3">
        All <span className="text-muted-foreground tabular">{total}</span>
      </ToggleGroupItem>
      {BANDS.map((b) => (
        <ToggleGroupItem key={b} value={b} className="gap-1.5 px-3">
          <Pennant className="size-3" color={bandStyle[b].hex} />
          {b} <span className="text-muted-foreground tabular">{counts[b]}</span>
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
