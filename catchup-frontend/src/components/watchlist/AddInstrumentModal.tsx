import { useEffect, useRef, useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { useApis } from "../../hooks/useApis";
import { useAddInstrument } from "../../hooks/useAddInstrument";
import { SearchBox } from "../search/SearchBox";

const EMPTY_IDS: ReadonlySet<string> = new Set();

export function AddInstrumentModal({
  open,
  onClose,
  watchedIds,
}: {
  open: boolean;
  onClose: () => void;
  watchedIds?: ReadonlySet<string>;
}) {
  const { instrument, watchlist } = useApis();
  const [query, setQuery] = useState("");
  const closeTimer = useRef<number | undefined>(undefined);
  const add = useAddInstrument(watchlist);
  const search = useAsync(
    () => query.trim() ? instrument.search(query.trim()) : Promise.resolve([]),
    [query, open],
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Reset per-open state (including the auto-close timer). Scoped to the
  // `open` transition only: depending on the useAddInstrument container would
  // re-run this effect on every render (fresh object identity) and busy-loop.
  useEffect(() => {
    if (open) {
      setQuery("");
      add.reset();
    }
    return () => window.clearTimeout(closeTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // The intended flow: success -> brief "Added" -> modal closes so the
  // watchlist refetches. Never auto-close over an error.
  useEffect(() => {
    if (!open || add.added.length === 0 || add.failed) return;
    closeTimer.current = window.setTimeout(onClose, 700);
    return () => window.clearTimeout(closeTimer.current);
  }, [add.added, add.failed, open, onClose]);

  if (!open) return null;

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

        <div className="mt-4">
          <SearchBox
            query={query}
            onQueryChange={(q) => {
              setQuery(q);
            }}
            results={search.status === "success" ? search.data : []}
            loading={search.status === "loading"}
            error={search.status === "error" ? search.error.message : null}
            onRetry={() => void search.reload()}
            watchedIds={watchedIds ?? EMPTY_IDS}
            addingId={add.addingId}
            addedIds={add.added}
            failed={add.failed}
            onAddInstrument={add.addInstrument}
            onAddSymbol={(symbol) => {
              add.addBySymbol(symbol);
              setQuery("");
            }}
            onRetryAdd={add.retry}
            autoFocus
          />
        </div>
      </div>
    </div>
  );
}