import type { ChangeSignal } from "../../domain/types";
import {
  formatPercentage, formatRatio, formatSigma,
} from "../../utils/formatting";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 text-sm">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="font-medium text-ink">{children}</dd>
    </div>
  );
}

export function WhyPanel({ signal }: { signal: ChangeSignal }) {
  return (
    <section aria-labelledby="why-heading" className="card p-5">
      <h2 id="why-heading" className="eyebrow">
        Why did this stand out?
      </h2>
      <dl className="mt-2 divide-y divide-line">
        <Row label="Price moved">{formatPercentage(signal.returnPct)}</Row>
        {signal.baselineMean !== null && (
          <Row label="Typical daily movement">±{signal.baselineMean.toFixed(1)}%</Row>
        )}
        <Row label="Unusualness">{formatSigma(signal.zScore)}</Row>
        <Row label="Volume">{formatRatio(signal.volumeRatio)} normal</Row>
        <Row label="Event">{signal.eventDescription}</Row>
      </dl>

      <h3 className="mt-5 eyebrow">Why am I seeing this?</h3>
      <ul className="mt-2 space-y-1.5 text-sm">
        {signal.reasonCodes.map((code) => (
          <li key={code} className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="flex h-4 w-4 items-center justify-center rounded-full bg-upsoft text-up"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                <path
                  d="M5 13l4 4L19 7"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="text-ink-soft">{reasonLabel(code)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const reasonLabels: Record<string, string> = {
  SIGNIFICANT_PRICE_MOVE: "Significant price movement",
  UNUSUAL_VOLUME: "Unusual volume",
  EARNINGS_EVENT: "Earnings event",
  CORPORATE_EVENT: "Corporate event",
  DATA_QUALITY: "Data quality concern",
};

function reasonLabel(code: string): string {
  return reasonLabels[code] ?? code.replaceAll("_", " ").toLowerCase();
}