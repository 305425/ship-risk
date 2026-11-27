import { createContext, useCallback, useContext, useState } from "react";
import { readScoringMode, writeScoringMode, type ScoringMode } from "@/lib/scoringMode";

interface ScoringModeValue {
  mode: ScoringMode;
  setMode: (mode: ScoringMode) => void;
}

const ScoringModeContext = createContext<ScoringModeValue | null>(null);

export function ScoringModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ScoringMode>(readScoringMode);

  const setMode = useCallback((next: ScoringMode) => {
    writeScoringMode(next);
    setModeState(next);
  }, []);

  return <ScoringModeContext.Provider value={{ mode, setMode }}>{children}</ScoringModeContext.Provider>;
}

export function useScoringMode() {
  const value = useContext(ScoringModeContext);
  if (!value) throw new Error("useScoringMode must be used within ScoringModeProvider");
  return value;
}
