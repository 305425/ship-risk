import { cn } from "@/lib/utils";

interface BrandLogoProps {
  variant?: "full" | "mark";
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizes = {
  sm: { mark: "h-6", text: "text-[11.5px]" },
  md: { mark: "h-7", text: "text-[13.5px]" },
  lg: { mark: "h-9", text: "text-[17px]" },
};

/** The flag is the logo image; the wordmark is live text so it stays sharp at small sizes. */
export function BrandLogo({ variant = "full", size = "md", className }: BrandLogoProps) {
  const s = sizes[size];
  const mark = (
    <img
      src="/brand/esm-mark.png"
      alt={variant === "mark" ? "Executive Ship Management" : ""}
      width={165}
      height={128}
      decoding="async"
      className={cn("block w-auto max-w-none shrink-0 object-contain", s.mark)}
    />
  );
  if (variant === "mark") return <span className={cn("inline-flex shrink-0", className)}>{mark}</span>;
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-2", className)} aria-label="Executive Ship Management">
      {mark}
      <span
        aria-hidden
        className={cn("font-sans leading-none font-medium tracking-[0.02em] whitespace-nowrap text-[#174a7c] uppercase", s.text)}
      >
        Executive Ship Management
      </span>
    </span>
  );
}
