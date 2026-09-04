import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { ChangeFeed } from "../components/catchup/ChangeFeed";
import { MarketStatusBanner } from "../components/catchup/MarketStatusBanner";
import { FirstVisitNotice } from "../components/catchup/FirstVisitNotice";
import { RelevancePrompt } from "../components/catchup/RelevancePrompt";
import { formatLastChecked } from "../utils/date";
import { useEffect } from "react";

export function CatchupPage() {
  const { catchup, watchlist } = useApis();
  const feed = useAsync(() => catchup.getFeed(), []);
  const list = useAsync(() => watchlist.getWatchlist(), []);
  const acknowledgement = feed.status === "success" ? feed.data.acknowledgement : undefined;

  // Acknowledge only the snapshots actually delivered in this rendered feed.
  // This prevents an ingestion run racing this request from being marked seen.
  useEffect(() => {
    if (!acknowledgement) return;
    void catchup.markSeen(acknowledgement);
  }, [acknowledgement, catchup]);

  if (feed.status === "loading") return <div className="py-16"><Spinner label="Checking what changed" /></div>;
  if (feed.status === "error") {
    return (
      <ErrorState
        title="Catchup could not check the market"
        message={feed.error.message}
        onRetry={feed.reload}
      />
    );
  }

  const { data } = feed;
  const hasWatchlist =
    list.status === "success" ? list.data.items.length > 0 : false;
  const meaningfulCount = data.changes.length;

  return (
    <div>
      <header className="mb-8">
        <h1 className="text-xl font-bold tracking-tight">CATCHUP</h1>
        <p className="mt-1 text-sm text-ink-muted">See what changed since you last checked.</p>
        <p className="mt-4 text-sm">
          Last checked:{" "}
          <span className="font-medium">
            {data.lastCheckedAt ? formatLastChecked(data.lastCheckedAt) : "this is your first check"}
          </span>
        </p>
        {data.lastCheckedAt && (
          <p className="mt-1 text-lg font-semibold">
            {meaningfulCount > 0
              ? `${meaningfulCount} thing${meaningfulCount === 1 ? "" : "s"} changed`
              : "Nothing meaningful changed."}
          </p>
        )}
      </header>

      {data.providerStatus === "UNAVAILABLE" && (
        <div role="alert" className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
          Market data is temporarily unavailable.
        </div>
      )}

      {data.lastCheckedAt === null ? (
        <FirstVisitNotice hasWatchlist={hasWatchlist} />
      ) : (
        <>
          {data.userRelevance && <RelevancePrompt relevance={data.userRelevance} />}
          <MarketStatusBanner feed={data} />
          {meaningfulCount > 0 ? (
            <ChangeFeed changes={data.changes} />
          ) : (
            <p className="text-sm text-ink-muted">
              {data.unchangedCount} stock{data.unchangedCount === 1 ? "" : "s"} checked.
            </p>
          )}
        </>
      )}
    </div>
  );
}
