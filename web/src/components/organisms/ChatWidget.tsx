import { useEffect, useRef, useState } from "react";
import { ExternalLink, MessageCircle, X } from "lucide-react";
import { signInFleetChat } from "@/api/client";
import { BrandLogo } from "@/components/atoms";
import { cn } from "@/lib/utils";

/** Floating launcher for the Chainlit assistant mounted at /chat. The iframe stays mounted so the session survives closing. */
export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const signedIn = useRef(false);

  const ensureSession = async () => {
    if (signedIn.current) return;
    signedIn.current = await signInFleetChat();
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const toggle = async () => {
    if (open) {
      setOpen(false);
      return;
    }
    await ensureSession();
    setLoaded(true);
    setOpen(true);
  };

  const openInTab = async (event: React.MouseEvent) => {
    event.preventDefault();
    await ensureSession();
    window.open("/chat/", "_blank");
  };

  return (
    <>
      {loaded && (
        <div
          role="dialog"
          aria-label="Fleet assistant"
          aria-hidden={!open}
          className={cn(
            "fixed right-5 bottom-24 z-40 flex w-[min(420px,calc(100vw-2.5rem))] origin-bottom-right flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl shadow-navy-900/25 transition duration-200",
            "h-[min(680px,calc(100vh-8rem))]",
            open ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-3 opacity-0",
          )}
        >
          <header className="flex h-12 shrink-0 items-center gap-2.5 bg-navy-900 px-3.5 text-white">
            <BrandLogo variant="mark" size="sm" className="[&_img]:h-5" />
            <span className="font-heading text-sm font-semibold tracking-wide">Fleet assistant</span>
            <a
              href="/chat/"
              onClick={openInTab}
              className="ml-auto rounded-md p-1.5 text-white/70 hover:bg-white/10 hover:text-white"
              aria-label="Open chat in a new tab"
              tabIndex={open ? 0 : -1}
            >
              <ExternalLink className="size-4" />
            </a>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-md p-1.5 text-white/70 hover:bg-white/10 hover:text-white"
              aria-label="Close chat"
              tabIndex={open ? 0 : -1}
            >
              <X className="size-4" />
            </button>
          </header>
          <div className="h-1 shrink-0 bg-silver" />
          <iframe src="/chat/" title="Fleet assistant" className="min-h-0 w-full flex-1 bg-white" tabIndex={open ? 0 : -1} />
        </div>
      )}
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-label={open ? "Close fleet assistant" : "Open fleet assistant"}
        className="fixed right-5 bottom-5 z-40 flex size-14 items-center justify-center rounded-full bg-navy-900 text-white shadow-lg shadow-navy-900/30 ring-4 ring-background transition-colors hover:bg-navy-800"
      >
        {open ? <X className="size-6" /> : <MessageCircle className="size-6" />}
      </button>
    </>
  );
}
