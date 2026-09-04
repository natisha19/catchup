import { Link } from "react-router-dom";
import type { ChangeSignal, MarketStatus } from "../../domain/types";
import { SignificanceBadge } from "../common/Badge";
import { DataStatusBadge } from "../common/DataStatusBadge";
import {
  formatCurrency, formatPercentage, formatRatio, formatSigma,
} from "../../utils/formatting";

const priceTone = (v: number | null) =>
  v === null ? "text-ink" : v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink";
const priceArrow = (v: number | null) =>
  v === null || v === 0 ? "·" : v > 0 ? "↑" : "↓";

export function ChangeCard({
  signal,
  marketStatus,
}: {
  signal: ChangeSignal;
  marketStatus?: MarketStatus;
}) {
  const isCritical = signal.significance === "CRITICAL";
  return (
    <article
      aria-label={`${signal.symbol}: ${signal.eventDescription}`}
      className={`card p-5 transition-shadow hover:shadow-raised ${
        isCritical ? "border-l-2 border-l-signal-critical" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5">
            <Link
              to={`/stock/${signal.instrumentId}`}
              className="text-base font-semibold text-ink hover:text-signal-notable hover:underline"
            >
              {signal.symbol}
            </Link>
            {signal.dataStatus !== "LIVE" && (
              <DataStatusBadge status={signal.dataStatus} marketStatus={marketStatus} />
            )}
          </div>
          <p className="mt-0.5 truncate text-sm text-ink-soft">{signal.companyName}</p>
          <p className="mt-1 text-sm font-medium text-ink">{signal.eventDescription}</p>
        </div>
        <div className="shrink-0">
          <SignificanceBadge tier={signal.significance} />
        </div>
      </div>

      <dl className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <div>
          <dt className="sr-only">Price</dt>
          <dd className="font-mono text-base font-medium text-ink">
            {formatCurrency(signal.currentPrice)}
          </dd>
        </div>
        <div className="flex items-baseline gap-1">
          <dt className="sr-only">Return</dt>
          <span aria-hidden className={`text-sm font-semibold ${priceTone(signal.returnPct)}`}>
            {priceArrow(signal.returnPct)}
          </span>
          <dd className={`text-sm font-semibold ${priceTone(signal.returnPct)}`}>
            {formatPercentage(signal.returnPct)}
          </dd>
        </div>
        <div className="text-sm text-ink-muted">
          <dt className="sr-only">Previous price</dt>
          <dd>
            {formatCurrency(signal.previousPrice)} → {formatCurrency(signal.currentPrice)}
          </dd>
        </div>
      </dl>

      {(signal.volumeRatio !== null || (signal.zScore !== null && signal.eventType !== "CORPORATE_EVENT")) && (
        <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t border-line pt-3 text-sm text-ink-muted">
          {signal.volumeRatio !== null && (
            <div>
              <dt className="sr-only">Volume versus normal</dt>
              <dd>
                Volume <span className="font-medium text-ink-soft">{formatRatio(signal.volumeRatio)}</span> normal
              </dd>
            </div>
          )}
          {signal.zScore !== null && signal.eventType !== "CORPORATE_EVENT" && (
            <div>
              <dt className="sr-only">Typical movement offset</dt>
              <dd>
                <span className="font-medium text-ink-soft">{formatSigma(signal.zScore)}</span> above typical movement
              </dd>
            </div>
          )}
        </dl>
      )}

      <Link
        to={`/stock/${signal.instrumentId}`}
        className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-signal-notable transition-colors hover:text-signal-notable/80"
      >
        Why this changed
        <span aria-hidden>→</span>
      </Link>
    </article>
  );
}