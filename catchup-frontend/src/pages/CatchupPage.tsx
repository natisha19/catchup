import { useEffect } from "react";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { ChangeFeed } from "../components/catchup/ChangeFeed";
import { MarketStatusBanner } from "../components/catchup/MarketStatusBanner";
import { MarketSnapshots } from "../components/catchup/MarketSnapshots";
import { FirstVisitNotice } from "../components/catchup/FirstVisitNotice";
import { RelevancePrompt } from "../components/catchup/RelevancePrompt";
import { formatLastChecked } from "../utils/date";
import { rememberMarketStatus } from "../domain/marketStatusCache";

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

  // Keep the latest market status available app-wide so "market closed" stays
  // recognizable on other pages without waiting on another feed round-trip.
  const resolvedFeed = feed.status === "success" ? feed.data : null;
  useEffect(() => {
    if (resolvedFeed) rememberMarketStatus(resolvedFeed.marketStatus);
  }, [resolvedFeed]);

  if (feed.status === "loading")
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner label="Checking what changed" />
      </div>
    );

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
  const watchedItems = list.status === "success" ? list.data.items : null;
  const watched = watchedItems?.length ?? null;
  const meaningfulCount = data.changes.length;
  const firstCheck = data.lastCheckedAt === null;

  return (
    <div className="space-y-8">
      <header className="max-w-2xl">
        <p className="eyebrow">Your catchup</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          See what changed since you last checked.
        </h1>
        {meaningfulCount > 0 && (
          <p className="mt-2 text-sm text-ink-muted">
            {meaningfulCount} thing{meaningfulCount === 1 ? "" : "s"} changed since then.
          </p>
        )}
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <dl className="card px-4 py-3.5 sm:px-5">
          <dt className="eyebrow">Last checked</dt>
          <dd className="mt-1 text-[15px] font-medium text-ink">
            {firstCheck
              ? "This is your first check"
              : formatLastChecked(data.lastCheckedAt)}
          </dd>
        </dl>
        <MarketStatusBanner feed={data} />
      </div>

      {data.providerStatus === "UNAVAILABLE" && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-downline bg-downsoft px-4 py-3 text-sm text-ink"
        >
          <span aria-hidden className="h-2 w-2 rounded-full bg-down" />
          Market data is temporarily unavailable.
        </div>
      )}

      {firstCheck ? (
        <FirstVisitNotice hasWatchlist={watched !== null && watched > 0} />
      ) : (
        <div className="space-y-8">
          {data.userRelevance && <RelevancePrompt relevance={data.userRelevance} />}

          {meaningfulCount > 0 ? (
            <ChangeFeed changes={data.changes} marketStatus={data.marketStatus} />
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
              {data.unchangedCount > 0 && (
                <span className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-upsoft px-3 py-1 text-xs font-semibold text-up">
                  <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-up" />
                  {data.unchangedCount} stock{data.unchangedCount === 1 ? "" : "s"} checked
                </span>
              )}
            </section>
          )}
        </div>
      )}

      {watched !== null && watched > 0 && list.status === "success" && (
        <MarketSnapshots items={list.data.items} marketStatus={data.marketStatus} />
      )}
    </div>
  );
}