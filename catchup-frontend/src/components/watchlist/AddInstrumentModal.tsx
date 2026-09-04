import { useEffect, useRef, useState } from "react";
import type { Instrument } from "../../domain/types";
import { useAsync } from "../../hooks/useAsync";
import { useApis } from "../../hooks/useApis";
import { Spinner } from "../common/Spinner";
import { ErrorState } from "../common/ErrorState";

type FailedAttempt =
  | { kind: "id"; instrument: Instrument }
  | { kind: "symbol"; symbol: string };

export function AddInstrumentModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { instrument, watchlist } = useApis();
  const [query, setQuery] = useState("");
  const [addingId, setAddingId] = useState<string | null>(null);
  const [added, setAdded] = useState<string[]>([]);
  const [failed, setFailed] = useState<FailedAttempt | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);

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

  // Reset per-open state (including the auto-close timer).
  useEffect(() => {
    if (open) {
      setAdded([]);
      setFailed(null);
      setAddingId(null);
    }
    return () => window.clearTimeout(closeTimer.current);
  }, [open]);

  // The intended flow: success -> brief "Added" -> modal closes so the
  // watchlist refetches. Never auto-close over an error.
  useEffect(() => {
    if (!open || added.length === 0 || failed) return;
    closeTimer.current = window.setTimeout(onClose, 700);
    return () => window.clearTimeout(closeTimer.current);
  }, [added, failed, open, onClose]);

  if (!open) return null;

  const attemptAdd = async (kind: "id", inst: Instrument) => {
    setAddingId(inst.instrumentId);
    setFailed(null);
    try {
      // instrumentId addresses an already-known instrument; symbol lets the
      // backend resolve + persist a catalog stock that has no row yet.
      await watchlist.addInstrument(inst.instrumentId, inst.symbol);
      setAdded((a) => [...a, inst.instrumentId]);
    } catch {
      setFailed({ kind, instrument: inst });
    } finally {
      setAddingId((a) => (a === inst.instrumentId ? null : a));
    }
  };

  const attemptAddBySymbol = async (symbol: string) => {
    setAddingId(symbol);
    setFailed(null);
    try {
      await watchlist.addInstrument("", symbol);
      setAdded((a) => [...a, symbol]);
      setQuery("");
    } catch {
      setFailed({ kind: "symbol", symbol });
    } finally {
      setAddingId((a) => (a === symbol ? null : a));
    }
  };

  const retry = () => {
    if (failed?.kind === "id") void attemptAdd("id", failed.instrument);
    else if (failed?.kind === "symbol") void attemptAddBySymbol(failed.symbol);
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
            onChange={(e) => {
              setQuery(e.target.value);
              setFailed(null);
            }}
            placeholder="Search by symbol or company…"
            aria-label="Search instruments"
            className="w-full rounded-lg border border-line bg-paper py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-muted focus:border-signal-notable focus:bg-card"
          />
        </div>

        {failed && (
          <div
            role="alert"
            className="mt-3 rounded-lg border border-downline bg-downsoft px-3.5 py-2.5"
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
              <button onClick={retry} className="text-xs font-semibold text-ink hover:text-ink-soft">
                Try again
              </button>
            </div>
          </div>
        )}

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
                onClick={() => void attemptAddBySymbol(query.trim())}
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
                onClick={() => void attemptAdd("id", inst)}
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