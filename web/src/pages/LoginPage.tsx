import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Loader2, LockKeyhole } from "lucide-react";
import { session, verifyApiKey } from "@/api/client";
import { BrandLogo, SilverRule } from "@/components/atoms";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/fleet";
  const [user, setUser] = useState(session.user);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session.isSignedIn()) return <Navigate to={from} replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (await verifyApiKey(apiKey)) {
        session.save(apiKey, user);
        navigate(from, { replace: true });
      } else {
        setError("Incorrect username or password.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy-50/40 px-4">
      <div className="w-full max-w-sm overflow-hidden rounded-xl border bg-white shadow-sm">
        <div className="flex h-16 items-center px-6">
          <BrandLogo size="md" />
        </div>
        <SilverRule className="h-[3px] rounded-none" />
        <form onSubmit={submit} className="space-y-5 px-6 pt-5 pb-6">
          <div className="space-y-1.5">
            <h1 className="flex items-center gap-2 text-lg font-semibold text-navy-900">
              <span className="flex size-7 items-center justify-center rounded-md bg-navy-50 text-navy-700">
                <LockKeyhole className="size-4" />
              </span>
              Sign in
            </h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Sign in once. Your session covers the dashboard, the fleet assistant and MLflow.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              autoComplete="username"
              placeholder="e.g. Capt. R. Menon"
              maxLength={100}
              className="h-10"
              required
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="current-password"
              className="h-10"
              required
            />
          </div>
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button type="submit" size="lg" className="w-full" disabled={busy}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : null}
            Sign in
          </Button>
        </form>
      </div>
    </main>
  );
}
