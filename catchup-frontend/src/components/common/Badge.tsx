import type { SignificanceTier } from "../../domain/types";

const tierStyles: Record<SignificanceTier, string> = {
  CRITICAL: "bg-signal-critical text-white",
  SIGNIFICANT: "bg-orange-50 text-signal-significant border border-orange-200",
  NOTABLE: "bg-blue-50 text-signal-notable border border-blue-200",
  NORMAL: "bg-gray-100 text-signal-normal border border-gray-200",
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
      className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold tracking-wide ${tierStyles[tier]}`}
      aria-label={`Significance: ${tierLabel[tier].toLowerCase()}`}
    >
      {tierLabel[tier]}
    </span>
  );
}
