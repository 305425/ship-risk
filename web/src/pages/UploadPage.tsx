import { PageHeader } from "@/components/molecules";
import { UploadHistory, UploadPanel } from "@/components/organisms";

export function UploadPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data management"
        title="Upload & versions"
        description="CSV uploads are validated row by row, stored as a new version of their table, and trigger a full fleet recalculation. Earlier versions are kept."
      />
      <UploadPanel />
      <UploadHistory />
    </div>
  );
}
