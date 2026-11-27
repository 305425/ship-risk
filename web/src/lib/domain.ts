import type { Band, ComponentKey } from "@/api/types";

export const BANDS: Band[] = ["High", "Medium", "Low"];

/** Band thresholds from rules.yaml; an override forces High regardless of score. */
export const BAND_THRESHOLDS = { high: 60, medium: 35 } as const;

export const bandStyle: Record<Band, { text: string; bg: string; soft: string; ring: string; hex: string; label: string }> = {
  High: {
    text: "text-band-high",
    bg: "bg-band-high",
    soft: "bg-band-high-soft",
    ring: "ring-band-high/25",
    hex: "#c2362b",
    label: "Act now",
  },
  Medium: {
    text: "text-band-medium",
    bg: "bg-band-medium",
    soft: "bg-band-medium-soft",
    ring: "ring-band-medium/25",
    hex: "#c77c02",
    label: "Watch",
  },
  Low: {
    text: "text-band-low",
    bg: "bg-band-low",
    soft: "bg-band-low-soft",
    ring: "ring-band-low/25",
    hex: "#23805a",
    label: "Routine",
  },
};

export const COMPONENTS: { key: ComponentKey; label: string; short: string }[] = [
  { key: "inspection", label: "Inspection history", short: "Inspection" },
  { key: "deficiencies", label: "Deficiencies", short: "Deficiencies" },
  { key: "maintenance", label: "Maintenance & equipment", short: "Maintenance" },
  { key: "crew", label: "Crew", short: "Crew" },
  { key: "audit", label: "Audit / ISM", short: "Audit" },
];

export const componentLabel = (key: string) => COMPONENTS.find((c) => c.key === key)?.short ?? key;

export const TABLE_LABELS: Record<string, string> = {
  vessels: "VesselMaster",
  inspections: "Inspections",
  deficiencies: "Deficiencies",
  detentions: "Detentions",
  audit_findings: "AuditFindings",
  crew: "Crew",
  equipment_failures: "EquipmentFailures",
  maintenance: "Maintenance",
};

export const EXPECTED_FILES = Object.values(TABLE_LABELS).map((t) => `${t}.csv`);

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export const formatDate = (iso: string | null | undefined) => (iso ? dateFmt.format(new Date(iso)) : "—");
export const formatDateTime = (iso: string | null | undefined) => (iso ? dateTimeFmt.format(new Date(iso)) : "—");

export function daysBetween(fromIso: string, toIso: string): number {
  const day = 86_400_000;
  return Math.round((Date.parse(toIso) - Date.parse(fromIso)) / day);
}

export const formatScore = (score: number) => score.toFixed(1);
