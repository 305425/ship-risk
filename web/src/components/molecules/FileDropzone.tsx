import { useRef, useState } from "react";
import { FileSpreadsheet, UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export function FileDropzone({ onFiles, disabled }: FileDropzoneProps) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const accept = (list: FileList | null) => {
    const files = Array.from(list ?? []).filter((f) => f.name.toLowerCase().endsWith(".csv"));
    if (files.length) onFiles(files);
  };

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        accept(e.dataTransfer.files);
      }}
      className={cn(
        "group relative flex w-full flex-col items-center justify-center gap-3 overflow-hidden rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
        over ? "border-navy-600 bg-navy-50" : "border-navy-100 bg-card hover:border-navy-600/60 hover:bg-navy-50/50",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <span className="flex size-12 items-center justify-center rounded-full bg-navy-900 text-white shadow-lg shadow-navy-900/20">
        <UploadCloud className="size-6" />
      </span>
      <div>
        <p className="font-heading text-sm font-semibold text-navy-900">Drop CSV files here, or click to browse</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Upload one or more of the 8 data tables. Each file fully replaces its table's current version.
        </p>
      </div>
      <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <FileSpreadsheet className="size-3.5" /> .csv only · up to 10 MB per file
      </span>
      <input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        multiple
        className="hidden"
        onChange={(e) => {
          accept(e.target.files);
          e.target.value = "";
        }}
      />
    </button>
  );
}
