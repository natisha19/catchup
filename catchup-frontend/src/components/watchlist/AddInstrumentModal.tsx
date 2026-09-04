import { useEffect, useRef, useState } from "react";
import type { Instrument } from "../../domain/types";
import { useAsync } from "../../hooks/useAsync";
import { useApis } from "../../hooks/useApis";
import { Spinner } from "../common/Spinner";
import { ErrorState } from "../common/ErrorState";

export function AddInstrumentModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { instrument, watchlist } = useApis();
  const [query, setQuery] = useState("");
  const [addingId, setAddingId] = useState<string | null>(null);
  const [added, setAdded] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const search = useAsync(
    () => query.trim() ? instrument.search(query.trim()) : Promise.resolve([]),
    [query, open],
  );

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const add = async (inst: Instrument) => {
    setAddingId(inst.instrumentId);
    try {
      await watchlist.addInstrument(inst.instrumentId);
      setAdded((a) => [...a, inst.instrumentId]);
    } finally {
      setAddingId(null);
    }
  };

  const addBySymbol = async () => {
    const symbol = query.trim();
    if (!symbol) return;
    setAddingId(symbol);
    try {
      await watchlist.addInstrument("", symbol);
      setAdded((a) => [...a, symbol]);
      setQuery("");
    } finally {
      setAddingId(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Add a stock"
      className="fixed inset-0 z-50 flex items-start justify-center bg-ink/40 p-4 pt-[10vh]"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="card w-full max-w-md animate-fade-in p-5 shadow-raised">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Add to watchlist</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-paper hover:text-ink"
          >
            <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="relative mt-4">
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
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by symbol or company…"
            aria-label="Search instruments"
            className="w-full rounded-lg border border-line bg-paper py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-muted focus:border-signal-notable focus:bg-card"
          />
        </div>

        <div className="mt-3 max-h-72 space-y-0.5 overflow-y-auto" aria-live="polite">
          {search.status === "loading" && (
            <div className="py-3"><Spinner label="Searching" /></div>
          )}
          {search.status === "error" && (
            <ErrorState title="Search failed" message={search.error.message} onRetry={search.reload} />
          )}
          {search.status === "success" && search.data.length === 0 && (
            query.trim() ? (
              <button
                onClick={addBySymbol}
                disabled={addingId != null}
                className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-paper disabled:opacity-60"
                aria-label={`Add ${query.trim()} by symbol`}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-ink">Add “{query.trim()}”</span>
                  <span className="block text-xs text-ink-muted">
                    not in catalog yet — resolve it
                  </span>
                </span>
                <span className="shrink-0 text-xs font-medium text-signal-notable">
                  {addingId === query.trim() ? "Adding…" : "Add to watchlist"}
                </span>
              </button>
            ) : (
              <p className="py-4 text-center text-sm text-ink-muted">No matches.</p>
            )
          )}
          {search.status === "success" && search.data.map(({ instrument: inst }) => {
            const isAdded = added.includes(inst.instrumentId);
            return (
              <button
                key={inst.instrumentId}
                onClick={() => add(inst)}
                disabled={isAdded || addingId === inst.instrumentId}
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
                  {isAdded ? "Added ✓" : addingId === inst.instrumentId ? "Adding…" : "Add to watchlist"}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}