import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ApiError } from "@/api/client";
import { AppShell } from "@/components/templates";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LandingPage } from "@/pages/LandingPage";
import { FleetPage } from "@/pages/FleetPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { UploadPage } from "@/pages/UploadPage";
import { ValidationPage } from "@/pages/ValidationPage";
import { VesselPage } from "@/pages/VesselPage";
import { ApiKeyProvider } from "@/providers/ApiKeyProvider";
import { RecordDetailProvider } from "@/providers/RecordDetailProvider";
import { ScoringModeProvider } from "@/providers/ScoringModeProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

function Root() {
  return (
    <ApiKeyProvider>
      <ScoringModeProvider>
        <RecordDetailProvider>
          <AppShell />
        </RecordDetailProvider>
      </ScoringModeProvider>
    </ApiKeyProvider>
  );
}

const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  {
    element: <Root />,
    children: [
      { path: "fleet", element: <FleetPage />, handle: { crumb: "Fleet risk" } },
      { path: "vessels/:vesselId", element: <VesselPage />, handle: { crumb: "Vessel report" } },
      { path: "upload", element: <UploadPage />, handle: { crumb: "Data upload" } },
      { path: "validation", element: <ValidationPage />, handle: { crumb: "Validation" } },
      { path: "*", element: <NotFoundPage />, handle: { crumb: "Not found" } },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={150}>
        <RouterProvider router={router} />
        <Toaster position="top-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
