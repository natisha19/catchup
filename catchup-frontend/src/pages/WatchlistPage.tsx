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
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Watchlist</h1>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-md bg-ink px-3 py-1.5 text-sm font-medium text-white hover:bg-ink-soft"
        >
          Add a stock
        </button>
      </div>

      {list.status === "loading" && <Spinner label="Loading watchlist" />}
      {list.status === "error" && (
        <ErrorState title="Could not load your watchlist" message={list.error.message} onRetry={list.reload} />
      )}
      {list.status === "success" && (
        list.data.items.length === 0
          ? <EmptyWatchlist />
          : <WatchlistTable items={list.data.items} onRemove={remove} />
      )}

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
