import { Outlet, ScrollRestoration } from "react-router-dom";
import { AppSidebar, ChatWidget, TopBar } from "@/components/organisms";
import { useScoringMode } from "@/providers/ScoringModeProvider";

export function AppShell() {
  const { mode } = useScoringMode();
  return (
    <div className="flex min-h-screen bg-chart-grid">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
        <footer className="border-t bg-card/60 px-4 py-3 text-[11px] text-muted-foreground md:px-8">
          Executive Ship Management · Ship Detention Early Warning System prototype ·{" "}
          {mode === "model"
            ? "Fleet scores follow the registered model. Actions stay with the rules."
            : "Scores are rule-based and advisory."}
        </footer>
      </div>
      <ChatWidget />
      <ScrollRestoration />
    </div>
  );
}
