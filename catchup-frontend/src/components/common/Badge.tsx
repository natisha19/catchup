import type { SignificanceTier } from "../../domain/types";

const tierStyles: Record<SignificanceTier, string> = {
  CRITICAL: "bg-downsoft text-down ring-1 ring-inset ring-downline",
  SIGNIFICANT: "bg-accent-soft text-signal-significant ring-1 ring-inset ring-accent-line",
  NOTABLE: "bg-blue-50 text-signal-notable ring-1 ring-inset ring-blue-200",
  NORMAL: "bg-paper text-signal-normal ring-1 ring-inset ring-line",
};

const tierLabel: Record<SignificanceTier, string> = {
  CRITICAL: "CRITICAL",
  SIGNIFICANT: "SIGNIFICANT",
  NOTABLE: "NOTABLE",
  NORMAL: "NORMAL",
};

export function SignificanceBadge({ tier }: { tier: SignificanceTier }) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold tracking-wide ${tierStyles[tier]}`}
      aria-label={`Significance: ${tierLabel[tier].toLowerCase()}`}
    >
      {tierLabel[tier]}
    </span>
  );
}