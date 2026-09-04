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

  const search = useAsync(() => instrument.search(query), [query, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

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
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-24"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md rounded-lg border border-line bg-white p-5 shadow-lg">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Add a stock</h2>
          <button onClick={onClose} aria-label="Close" className="text-ink-muted hover:text-ink">✕</button>
        </div>
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by symbol or company…"
          aria-label="Search instruments"
          className="mt-4 w-full rounded-md border border-line px-3 py-2 text-sm focus:border-s-notable"
        />
        <div className="mt-3 max-h-64 space-y-1 overflow-y-auto" aria-live="polite">
          {search.status === "loading" && <Spinner label="Searching" />}
          {search.status === "error" && (
            <ErrorState title="Search failed" message={search.error.message} onRetry={search.reload} />
          )}
          {search.status === "success" && search.data.length === 0 && (
            query.trim() ? (
              <button
                onClick={addBySymbol}
                disabled={addingId != null}
                className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-gray-50 disabled:opacity-60"
                aria-label={`Add ${query.trim()} by symbol`}
              >
                <span>
                  <span className="font-medium">Add “{query.trim()}”</span>
                  <span className="ml-2 text-ink-muted">not in catalog yet — resolve it</span>
                </span>
                <span className="text-xs font-medium text-signal-notable">
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
                className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-gray-50 disabled:opacity-60"
              >
                <span>
                  <span className="font-medium">{inst.companyName}</span>
                  <span className="ml-2 text-ink-muted">{inst.symbol} · {inst.exchange}</span>
                </span>
                <span className="text-xs font-medium text-signal-notable">
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
