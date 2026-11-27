import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { EmptyState } from "@/components/molecules";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <EmptyState
      icon={Compass}
      title="Off the chart"
      description="This page doesn't exist."
      action={<Button asChild><Link to="/">Back to fleet</Link></Button>}
      className="mt-16"
    />
  );
}
