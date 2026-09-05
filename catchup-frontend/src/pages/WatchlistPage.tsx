import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { WatchlistTable } from "../components/watchlist/WatchlistTable";
import { EmptyWatchlist } from "../components/watchlist/EmptyWatchlist";
import { AddInstrumentModal } from "../components/watchlist/AddInstrumentModal";
import { ChangeFeed } from "../components/catchup/ChangeFeed";
import { MarketStatusBanner } from "../components/catchup/MarketStatusBanner";
import { MarketSnapshots } from "../components/catchup/MarketSnapshots";
import { FirstVisitNotice } from "../components/catchup/FirstVisitNotice";
import { RelevancePrompt } from "../components/catchup/RelevancePrompt";
import { formatLastChecked } from "../utils/date";
import { rememberMarketStatus } from "../domain/marketStatusCache";

/**
 * The Catchup page (spec): what changed since you last checked, plus the
 * watchlist it manages. Home ("/") is Explore; this is where Catchup lives.
 */
export function WatchlistPage() {
  const { catchup, watchlist } = useApis();
  const [params, setParams] = useSearchParams();
  const [modalOpen, setModalOpen] = useState(params.get("add") === "1");
  const [reviewing, setReviewing] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const feed = useAsync(() => catchup.getFeed(), []);
  const list = useAsync(() => watchlist.getWatchlist(), []);
  const acknowledgement = feed.status === "success" ? feed.data.acknowledgement : undefined;

  useEffect(() => {
    if (params.get("add") === "1") {
      setModalOpen(true);
      setParams({}, { replace: true });
    }
  }, [params, setParams]);

  // Keep the latest market status available app-wide so "market closed" stays
  // recognizable on other pages without waiting on another feed round-trip.
  const resolvedFeed = feed.status === "success" ? feed.data : null;
  useEffect(() => {
    if (resolvedFeed) rememberMarketStatus(resolvedFeed.marketStatus);
  }, [resolvedFeed]);

  const remove = async (instrumentId: string) => {
    await watchlist.removeInstrument(instrumentId);
    list.reload();
  };

  const markReviewed = async () => {
    if (!acknowledgement || reviewing || reviewed) return;
    setReviewing(true);
    try {
      // Acknowledge only the snapshot watermark in this rendered feed. A
      // concurrent ingestion run is deliberately left unseen for next time.
      await catchup.markSeen(acknowledgement);
      setReviewed(true);
    } finally {
      setReviewing(false);
    }
  };

  const items = list.status === "success" ? list.data.items : null;
  const watched = items?.length ?? 0;
  const watchedIds = new Set((items ?? []).map((i) => i.instrument.instrumentId));

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">Your catchup</p>
          <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-ink">
            What changed since you last checked.
          </h1>
          {resolvedFeed && (
            <p className="mt-1 text-sm text-ink-muted">
              {resolvedFeed.changes.length > 0 ? (
                <>
                  {resolvedFeed.changes.length} thing
                  {resolvedFeed.changes.length === 1 ? "" : "s"} changed since then.
                </>
              ) : (
                <>
                  {watched} stock{watched === 1 ? "" : "s"} monitored
                </>
              )}
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
      </header>

      {feed.status === "loading" && (
        <div className="flex min-h-[25vh] items-center justify-center">
          <Spinner label="Checking what changed" />
        </div>
      )}
      {feed.status === "error" && (
        <ErrorState
          title="Catchup could not check the market"
          message={feed.error.message}
          onRetry={feed.reload}
        />
      )}
      {feed.status === "success" && resolvedFeed && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <dl className="card px-4 py-3.5 sm:px-5">
              <dt className="eyebrow">Last checked</dt>
              <dd className="mt-1 text-[15px] font-medium text-ink">
                {resolvedFeed.lastCheckedAt === null
                  ? "This is your first check"
                  : formatLastChecked(resolvedFeed.lastCheckedAt)}
              </dd>
            </dl>
            <MarketStatusBanner feed={resolvedFeed} />
          </div>

          {resolvedFeed.providerStatus === "UNAVAILABLE" && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-lg border border-downline bg-downsoft px-4 py-3 text-sm text-ink"
            >
              <span aria-hidden className="h-2 w-2 rounded-full bg-down" />
              Market data is temporarily unavailable.
            </div>
          )}

          {resolvedFeed.lastCheckedAt === null ? (
            <div className="space-y-4">
              <FirstVisitNotice hasWatchlist={watched > 0} />
              {watched > 0 && (
                <div className="flex justify-end">
                  <button
                    type="button"
                    className="btn px-3 py-1.5 text-xs"
                    onClick={() => void markReviewed()}
                    disabled={reviewing || reviewed}
                  >
                    {reviewed ? "Initial check saved" : reviewing ? "Saving…" : "Start tracking from here"}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-8">
              {resolvedFeed.userRelevance && (
                <RelevancePrompt relevance={resolvedFeed.userRelevance} />
              )}
              {resolvedFeed.changes.length > 0 ? (
                <ChangeFeed
                  changes={resolvedFeed.changes}
                  marketStatus={resolvedFeed.marketStatus}
                />
              ) : (
                <section
                  aria-live="polite"
                  className="card flex flex-col items-center px-6 py-12 text-center sm:py-16"
                >
                  <span
                    aria-hidden
                    className="flex h-14 w-14 items-center justify-center rounded-full bg-upsoft text-up ring-1 ring-inset ring-upline"
                  >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
                      <path
                        d="M5 13l4 4L19 7"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  <h2 className="mt-5 text-2xl font-semibold tracking-tight text-ink">
                    Nothing meaningful changed
                  </h2>
                  <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-muted">
                    Your watchlist looks much like it did the last time you checked.
                  </p>
                  {resolvedFeed.unchangedCount > 0 && (
                    <span className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-upsoft px-3 py-1 text-xs font-semibold text-up">
                      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-up" />
                      {resolvedFeed.unchangedCount} stock
                      {resolvedFeed.unchangedCount === 1 ? "" : "s"} checked
                    </span>
                  )}
                </section>
              )}
              {watched > 0 && (
                <div className="flex justify-end">
                  <button
                    type="button"
                    className="btn px-3 py-1.5 text-xs"
                    onClick={() => void markReviewed()}
                    disabled={reviewing || reviewed}
                  >
                    {reviewed ? "Catch-up reviewed" : reviewing ? "Saving…" : "Mark catch-up reviewed"}
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      <div>
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
          watched === 0
            ? <EmptyWatchlist />
            : <WatchlistTable items={list.data.items} onRemove={remove} />
        )}
      </div>

      {list.status === "success" && watched > 0 && (
        <MarketSnapshots items={list.data.items} marketStatus={resolvedFeed?.marketStatus} />
      )}

      <AddInstrumentModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          list.reload();
        }}
        watchedIds={watchedIds}
      />
    </div>
  );
}
