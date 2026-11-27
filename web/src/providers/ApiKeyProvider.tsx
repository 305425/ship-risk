import { createContext, useCallback, useContext, useEffect } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { session, UNAUTHORIZED_EVENT } from "@/api/client";

interface ApiKeyContextValue {
  /** Sign out and return to the login screen. */
  open: () => void;
  user: string;
}

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

/** Guards the dashboard: no stored sign-in means the login screen. */
export function ApiKeyProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const signedIn = session.isSignedIn();

  const signOut = useCallback(() => {
    session.clear();
    qc.clear();
    navigate("/login", { replace: true });
  }, [navigate, qc]);

  useEffect(() => {
    if (signedIn) session.sync();
    window.addEventListener(UNAUTHORIZED_EVENT, signOut);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, signOut);
  }, [signedIn, signOut]);

  if (!signedIn) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }

  return <ApiKeyContext.Provider value={{ open: signOut, user: session.user() }}>{children}</ApiKeyContext.Provider>;
}

export function useApiKeyDialog() {
  const ctx = useContext(ApiKeyContext);
  if (!ctx) throw new Error("useApiKeyDialog must be used inside ApiKeyProvider");
  return ctx;
}
