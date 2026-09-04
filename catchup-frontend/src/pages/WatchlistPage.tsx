import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { WatchlistTable } from "../components/watchlist/WatchlistTable";
import { EmptyWatchlist } from "../components/watchlist/EmptyWatchlist";
import { AddInstrumentModal } from "../components/watchlist/AddInstrumentModal";

export function WatchlistPage() {
  const { watchlist } = useApis();
  const [params, setParams] = useSearchParams();
  const [modalOpen, setModalOpen] = useState(params.get("add") === "1");
  const list = useAsync(() => watchlist.getWatchlist(), []);

  useEffect(() => {
    if (params.get("add") === "1") {
      setModalOpen(true);
      setParams({}, { replace: true });
    }
  }, [params, setParams]);

  const remove = async (instrumentId: string) => {
    await watchlist.removeInstrument(instrumentId);
    list.reload();
  };

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">Watchlist</p>
          <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-ink">
            Stocks you&apos;re watching
          </h1>
          {list.status === "success" && (
            <p className="mt-1 text-sm text-ink-muted">
              {list.data.items.length} stock{list.data.items.length === 1 ? "" : "s"} monitored
            </p>
          )}
        </div>
        <button onClick={() => setModalOpen(true)} className="btn-primary shrink-0">
          <span aria-hidden>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5v14M5 12h14"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </span>
          Add a stock
        </button>
      </div>

      <div className="mt-8">
        {list.status === "loading" && (
          <div className="py-8"><Spinner label="Loading watchlist" /></div>
        )}
        {list.status === "error" && (
          <ErrorState
            title="Could not load your watchlist"
            message={list.error.message}
            onRetry={list.reload}
          />
        )}
        {list.status === "success" && (
          list.data.items.length === 0
            ? <EmptyWatchlist />
            : <WatchlistTable items={list.data.items} onRemove={remove} />
        )}
      </div>

      <AddInstrumentModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          list.reload();
        }}
      />
    </div>
  );
}