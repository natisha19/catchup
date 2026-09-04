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
    <ul className="divide-y divide-line rounded-lg border border-line bg-white">
      {items.map(({ instrument, addedAt, baselineStatus }) => (
        <li key={instrument.instrumentId} className="flex items-center justify-between gap-3 px-4 py-3">
          <div>
            <Link to={`/stock/${instrument.instrumentId}`} className="font-medium hover:underline">
              {instrument.symbol}
            </Link>
            <p className="text-sm text-ink-muted">
              {instrument.companyName} · {instrument.exchange}
            </p>
            {baselineStatus === "INSUFFICIENT" && (
              <p className="mt-0.5 text-xs italic text-signal-significant">Baseline being established.</p>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-xs text-ink-muted sm:inline">
              Added {formatTimestamp(addedAt)}
            </span>
            <button
              onClick={() => onRemove(instrument.instrumentId)}
              aria-label={`Remove ${instrument.symbol} from watchlist`}
              className="rounded-md border border-line px-2.5 py-1 text-xs font-medium text-ink-soft hover:bg-gray-50"
            >
              Remove
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
