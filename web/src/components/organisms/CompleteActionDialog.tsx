import { useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useCompleteAction } from "@/api/hooks";
import type { CompleteActionResult, VesselAction } from "@/api/types";
import { OwnerTag } from "@/components/atoms";
import { ReadinessDelta, RecordIdList } from "@/components/molecules";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  vesselId: string;
  action: VesselAction | null;
  onClose: () => void;
}

export function CompleteActionDialog({ vesselId, action, onClose }: Props) {
  const complete = useCompleteAction(vesselId);
  const [evidence, setEvidence] = useState("");
  const [result, setResult] = useState<CompleteActionResult | null>(null);

  const close = () => {
    setEvidence("");
    setResult(null);
    complete.reset();
    onClose();
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!action) return;
    complete.mutate(
      { actionId: action.id, evidence: evidence.trim() },
      {
        onSuccess: (res) => {
          setResult(res);
          toast.success("Action completed", { description: `Readiness ${res.readiness.text}` });
        },
      },
    );
  };

  return (
    <Dialog open={!!action} onOpenChange={(o) => !o && close()}>
      <DialogContent className="sm:max-w-lg">
        {result ? (
          <div className="space-y-5">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 font-heading text-navy-900">
                <CheckCircle2 className="size-5 text-band-low" /> Action completed
              </DialogTitle>
              <DialogDescription>The score was recalculated with the resolved records. Readiness change:</DialogDescription>
            </DialogHeader>
            <div className="rounded-lg border bg-muted/40 p-4">
              <ReadinessDelta readiness={result.readiness} />
            </div>
            <DialogFooter>
              <Button onClick={close}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          action && (
            <form onSubmit={submit} className="space-y-5">
              <DialogHeader>
                <DialogTitle className="font-heading text-navy-900">Complete action</DialogTitle>
                <DialogDescription>{action.text}</DialogDescription>
              </DialogHeader>
              <div className="flex flex-wrap items-center gap-2">
                <OwnerTag owner={action.owner} />
                <RecordIdList ids={action.record_ids} max={6} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="evidence">Completion evidence</Label>
                <Textarea
                  id="evidence"
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                  rows={4}
                  minLength={3}
                  maxLength={2000}
                  required
                  placeholder="What was done, by whom, and the reference (work order, certificate number, test report)…"
                />
                <p className="text-xs text-muted-foreground">Recorded in the audit log with your name.</p>
              </div>
              {complete.error && <p className="text-sm text-destructive">{complete.error.message}</p>}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={close}>Cancel</Button>
                <Button type="submit" disabled={complete.isPending || evidence.trim().length < 3}>
                  {complete.isPending && <Loader2 className="size-4 animate-spin" />}
                  Complete and recalculate
                </Button>
              </DialogFooter>
            </form>
          )
        )}
      </DialogContent>
    </Dialog>
  );
}
