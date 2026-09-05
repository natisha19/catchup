import type { Instrument } from "../../domain/types";
import { Spinner } from "../common/Spinner";
import { ErrorState } from "../common/ErrorState";

export type AddFailed =
  | { kind: "id"; instrument: Instrument }
  | { kind: "symbol"; symbol: string };

/**
 * Presentational search box shared by the Explore hero and the add-to-watchlist
 * modal. All state and actions come from the page so the component stays pure:
 * nothing here decides add feedback, dedupes, or derives filtering.
 */
export function SearchBox({
  query,
  onQueryChange,
  results,
  loading,
  error,
  onRetry,
  watchedIds,
  addingId,
  addedIds,
  failed,
  onAddInstrument,
  onAddSymbol,
  onRetryAdd,
  autoFocus,
  ariaLabel = "Search instruments",
}: {
  query: string;
  onQueryChange: (q: string) => void;
  results: { instrument: Instrument }[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  watchedIds: ReadonlySet<string>;
  addingId: string | null;
  addedIds: string[];
  failed: AddFailed | null;
  onAddInstrument: (instrument: Instrument) => void;
  onAddSymbol: (symbol: string) => void;
  onRetryAdd: () => void;
  autoFocus?: boolean;
  ariaLabel?: string;
}) {
  const trimmed = query.trim();
  const isAdded = (id: string) => addedIds.includes(id);
  const isWatched = (id: string) => watchedIds.has(id);
  // Already-watched instruments are filtered out of results: this search is for
  // *adding new* stocks, so watched rows are noise. If every match is already
  // watched, we say so explicitly instead of rendering inert rows.
  const visible = results.filter((r) => !isWatched(r.instrument.instrumentId));

  return (
    <div>
      <div className="relative">
        <span
          aria-hidden
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
            <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </span>
        <input
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => {
            onQueryChange(e.target.value);
          }}
          placeholder="Search by symbol or company…"
          aria-label={ariaLabel}
          className="w-full rounded-lg border border-line bg-paper py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-muted focus:border-signal-notable focus:bg-card"
        />
      </div>

      {failed && (
        <div
          role="alert"
          className="mt-2 rounded-lg border border-downline bg-downsoft px-3.5 py-2.5"
        >
          <p className="text-sm font-medium text-down">
            Unable to add{" "}
            <span className="font-semibold">
              {failed.kind === "id" ? failed.instrument.symbol : failed.symbol}
            </span>
          </p>
          <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-ink-soft">
              It&apos;s already in your watchlist, or the API rejected it.
            </p>
            <button onClick={onRetryAdd} className="text-xs font-semibold text-ink hover:text-ink-soft">
              Try again
            </button>
          </div>
        </div>
      )}

      <div className="mt-2 max-h-72 space-y-0.5 overflow-y-auto" aria-live="polite">
        {loading && (
          <div className="py-3"><Spinner label="Searching" /></div>
        )}
        {error && (
          <ErrorState title="Search failed" message={error} onRetry={onRetry} />
        )}
        {!loading && !error && visible.length === 0 && (
          results.length > 0 ? (
            <div role="status" className="py-3 text-center text-sm text-ink-muted">
              “{trimmed}” is already in your watchlist — try another symbol.
            </div>
          ) : trimmed ? (
            <button
              onClick={() => onAddSymbol(trimmed)}
              disabled={addingId != null}
              className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-paper disabled:opacity-60"
              aria-label={`Add ${trimmed} by symbol`}
            >
              <span className="min-w-0">
                <span className="block truncate font-medium text-ink">Add “{trimmed}”</span>
                <span className="block text-xs text-ink-muted">
                  not in catalog yet — resolve it
                </span>
              </span>
              <span className="shrink-0 text-xs font-medium text-signal-notable">
                {addingId === trimmed ? "Adding…" : "Add to watchlist"}
              </span>
            </button>
          ) : (
            <p className="py-4 text-center text-sm text-ink-muted">No matches.</p>
          )
        )}
        {!loading && !error &&
          visible.map(({ instrument: inst }) => {
            const addedFlag = isAdded(inst.instrumentId);
            const busy = addingId === inst.instrumentId;
            return (
              <button
                key={inst.instrumentId}
                onClick={() => onAddInstrument(inst)}
                disabled={addedFlag || busy}
                className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-paper disabled:opacity-60"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-ink">{inst.companyName}</span>
                  <span className="block text-xs text-ink-muted">
                    {inst.symbol} · {inst.exchange}
                    {inst.currency ? ` · ${inst.currency}` : ""}
                  </span>
                </span>
                <span className="shrink-0 text-xs font-medium text-signal-notable">
                  {addedFlag ? "Added ✓" : busy ? "Adding…" : "Add to watchlist"}
                </span>
              </button>
            );
          })}
      </div>
    </div>
  );
}