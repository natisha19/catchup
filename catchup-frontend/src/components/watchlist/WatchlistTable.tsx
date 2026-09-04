import { Link } from "react-router-dom";
import type { WatchlistItem } from "../../domain/types";
import { formatTimestamp } from "../../utils/date";

export function WatchlistTable({
  items,
  onRemove,
}: {
  items: WatchlistItem[];
  onRemove: (instrumentId: string) => void;
}) {
  return (
    <ul className="card overflow-hidden">
      {items.map(({ instrument, addedAt, baselineStatus }) => (
        <li
          key={instrument.instrumentId}
          className="flex items-center justify-between gap-4 border-b border-line px-4 py-5 last:border-b-0 sm:px-5"
        >
          <div className="min-w-0">
            <Link
              to={`/stock/${instrument.instrumentId}`}
              className="text-xl font-semibold tracking-tight text-ink hover:text-signal-notable hover:underline"
            >
              {instrument.symbol}
            </Link>
            <p className="mt-0.5 truncate text-sm text-ink-muted">
              {instrument.companyName}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-paper px-2 py-0.5 text-[11px] font-medium text-ink-soft ring-1 ring-inset ring-line">
                {instrument.exchange}
                {instrument.currency ? ` · ${instrument.currency}` : ""}
              </span>
              {baselineStatus === "INSUFFICIENT" && (
                <span className="inline-flex items-center text-xs font-medium text-signal-significant">
                  <span aria-hidden className="mr-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
                  Baseline being established.
                </span>
              )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-3 sm:gap-5">
            <span className="hidden text-xs text-ink-muted lg:inline">
              Added {formatTimestamp(addedAt)}
            </span>
            <Link to={`/stock/${instrument.instrumentId}`} aria-label={`View ${instrument.symbol}`}>
              <svg
                aria-hidden
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                className="text-ink-muted transition-colors hover:text-ink"
              >
                <path
                  d="M9 6l6 6-6 6"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </Link>
            <button
              onClick={() => onRemove(instrument.instrumentId)}
              aria-label={`Remove ${instrument.symbol} from watchlist`}
              className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium text-ink-soft transition-colors hover:border-downline hover:bg-downsoft hover:text-down"
            >
              Remove
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}