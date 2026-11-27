import { createContext, useCallback, useContext, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { session } from "@/api/client";
import { BrandLogo, SilverRule } from "@/components/atoms";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ApiKeyContextValue {
  open: () => void;
  user: string;
}

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const [isOpen, setOpen] = useState(() => !session.apiKey());
  const [apiKey, setApiKey] = useState(session.apiKey);
  const [user, setUser] = useState(session.user);

  const open = useCallback(() => {
    setApiKey(session.apiKey());
    setUser(session.user());
    setOpen(true);
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    session.save(apiKey, user);
    setOpen(false);
    qc.invalidateQueries();
  };

  return (
    <ApiKeyContext.Provider value={{ open, user: session.user() }}>
      {children}
      <Dialog open={isOpen} onOpenChange={setOpen}>
        <DialogContent className="gap-0 overflow-hidden p-0 sm:max-w-md [&>[data-slot=dialog-close]]:top-4 [&>[data-slot=dialog-close]]:right-4">
          <div className="flex h-16 items-center px-6 pr-16">
            <BrandLogo size="md" />
          </div>
          <SilverRule className="h-[3px] rounded-none" />
          <form onSubmit={submit}>
            <div className="space-y-5 px-6 pt-5 pb-6">
              <DialogHeader className="gap-1.5 text-left">
                <DialogTitle className="flex items-center gap-2 text-lg font-semibold text-navy-900">
                  <span className="flex size-7 items-center justify-center rounded-md bg-navy-50 text-navy-700">
                    <KeyRound className="size-4" />
                  </span>
                  Connect to the risk service
                </DialogTitle>
                <DialogDescription className="leading-relaxed">
                  The prototype uses a single API key, sent with every request. Your name is recorded in the audit log
                  for uploads and completed actions.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                <Label htmlFor="api-key">API key</Label>
                <Input
                  id="api-key"
                  type="password"
                  autoComplete="off"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="X-API-Key value from .env"
                  className="h-10"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="user">Your name</Label>
                <Input
                  id="user"
                  value={user}
                  onChange={(e) => setUser(e.target.value)}
                  placeholder="e.g. Capt. R. Menon"
                  maxLength={100}
                  className="h-10"
                />
              </div>
            </div>
            <DialogFooter className="mx-0 mb-0 rounded-none px-6 py-4">
              <Button type="submit" size="lg" className="w-full sm:w-auto sm:px-6">Connect</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </ApiKeyContext.Provider>
  );
}

export function useApiKeyDialog() {
  const ctx = useContext(ApiKeyContext);
  if (!ctx) throw new Error("useApiKeyDialog must be used inside ApiKeyProvider");
  return ctx;
}
