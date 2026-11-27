import { OctagonX } from "lucide-react";
import type { RowError } from "@/api/types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function ValidationErrors({ errors }: { errors: RowError[] }) {
  const files = new Set(errors.map((e) => e.file)).size;
  return (
    <div className="space-y-3">
      <Alert variant="destructive" className="border-band-high/30 bg-band-high-soft">
        <OctagonX className="size-4" />
        <AlertTitle>Upload rejected. Nothing was saved.</AlertTitle>
        <AlertDescription>
          {errors.length} problem{errors.length === 1 ? "" : "s"} across {files} file{files === 1 ? "" : "s"}. Fix the rows below and upload again.
        </AlertDescription>
      </Alert>
      <div className="max-h-96 overflow-auto rounded-lg border">
        <Table>
          <TableHeader className="sticky top-0 bg-muted">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-40">File</TableHead>
              <TableHead className="w-16">Row</TableHead>
              <TableHead className="w-44">Column</TableHead>
              <TableHead className="w-40">Value</TableHead>
              <TableHead>Problem</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {errors.map((e, i) => (
              <TableRow key={i}>
                <TableCell className="text-xs font-medium">{e.file || "—"}</TableCell>
                <TableCell className="font-mono text-xs tabular">{e.row ?? "—"}</TableCell>
                <TableCell className="font-mono text-xs">{e.column ?? "—"}</TableCell>
                <TableCell className="max-w-40 truncate font-mono text-xs text-band-high" title={e.value ?? ""}>{e.value ?? "—"}</TableCell>
                <TableCell className="text-xs whitespace-normal">{e.message}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
