import { Link } from "react-router-dom";
import type { ChangeSignal } from "../../domain/types";
import { SignificanceBadge } from "../common/Badge";
import { DataStatusBadge } from "../common/DataStatusBadge";
import {
  formatCurrency, formatPercentage, formatRatio, formatSigma,
} from "../../utils/formatting";

const priceTone = (v: number | null) =>
  v === null ? "text-ink" : v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink";

export function ChangeCard({ signal }: { signal: ChangeSignal }) {
  return (
    <article
      aria-label={`signal.symbol:{signal.symbol}:signal.symbol:{signal.eventDescription}`}
      className={`rounded-lg border bg-white p-5 ${
        signal.significance === "CRITICAL"
          ? "border-signal-critical border-l-4 border-l-signal-critical shadow-sm"
          : "border-line"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link
            to={`/stock/${signal.instrumentId}`}
            className="text-base font-semibold hover:underline"
          >
            {signal.symbol}
          </Link>
          <p className="text-sm text-ink-soft">{signal.eventDescription}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <SignificanceBadge tier={signal.significance} />
          {signal.dataStatus !== "LIVE" && <DataStatusBadge status={signal.dataStatus} />}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="font-mono text-sm text-ink-soft">
          {formatCurrency(signal.previousPrice)} → {formatCurrency(signal.currentPrice)}
        </span>
        <span className={`font-semibold ${priceTone(signal.returnPct)}`}>
          {formatPercentage(signal.returnPct)}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-muted">
        {signal.volumeRatio !== null && (
          <span>Volume <span className="text-ink-soft">{formatRatio(signal.volumeRatio)}</span> normal</span>
        )}
        {signal.zScore !== null && signal.eventType !== "CORPORATE_EVENT" && (
          <span>{formatSigma(signal.zScore)} above typical movement</span>
        )}
      </div>

      <Link
        to={`/stock/${signal.instrumentId}`}
        className="mt-4 inline-block text-sm font-medium text-signal-notable hover:underline"
      >
        Why this changed →
      </Link>
    </article>
  );
}
