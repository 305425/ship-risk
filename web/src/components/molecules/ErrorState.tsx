import { KeyRound, TriangleAlert } from "lucide-react";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { useApiKeyDialog } from "@/providers/ApiKeyProvider";
import { EmptyState } from "./EmptyState";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { open } = useApiKeyDialog();
  if (error instanceof ApiError && error.status === 401) {
    return (
      <EmptyState
        icon={KeyRound}
        title="Session expired"
        description="Sign in again to load fleet data."
        action={<Button onClick={open}>Sign in</Button>}
      />
    );
  }
  const message = error instanceof Error ? error.message : "Something went wrong";
  return (
    <EmptyState
      icon={TriangleAlert}
      title="Couldn't load this data"
      description={message}
      action={onRetry && <Button variant="outline" onClick={onRetry}>Try again</Button>}
    />
  );
}
