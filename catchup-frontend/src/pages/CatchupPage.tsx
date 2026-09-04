import { Link } from "react-router-dom";
import { useEffect } from "react";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { ChangeFeed } from "../components/catchup/ChangeFeed";
import { MarketStatusBanner } from "../components/catchup/MarketStatusBanner";
import { FirstVisitNotice } from "../components/catchup/FirstVisitNotice";
import { RelevancePrompt } from "../components/catchup/RelevancePrompt";
import { formatLastChecked } from "../utils/date";

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
  const watched = list.status === "success" ? list.data.items.length : null;
  const meaningfulCount = data.changes.length;
  const firstCheck = data.lastCheckedAt === null;

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-xl">
          <p className="eyebrow">Your catchup</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            See what changed since you last checked.
          </h1>
          {meaningfulCount > 0 && (
            <p className="mt-2 text-sm text-ink-muted">
              {meaningfulCount} thing{meaningfulCount === 1 ? "" : "s"} changed since then.
            </p>
          )}
        </div>
        <dl className="shrink-0">
          <dt className="eyebrow">Last checked</dt>
          <dd className="mt-1 text-[15px] font-medium text-ink">
            {firstCheck
              ? "This is your first check"
              : formatLastChecked(data.lastCheckedAt)}
          </dd>
        </dl>
      </header>

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
        <FirstVisitNotice hasWatchlist={list.status === "success" && list.data.items.length > 0} />
      ) : (
        <div className="space-y-8">
          {data.userRelevance && <RelevancePrompt relevance={data.userRelevance} />}
          <MarketStatusBanner feed={data} />

          {meaningfulCount > 0 ? (
            <ChangeFeed changes={data.changes} />
          ) : (
            <section
              aria-live="polite"
              className="card flex flex-col items-center px-6 py-12 text-center sm:py-14"
            >
              <span
                aria-hidden
                className="flex h-12 w-12 items-center justify-center rounded-full bg-upsoft text-up"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path
                    d="M5 13l4 4L19 7"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
              <h2 className="mt-5 text-xl font-semibold text-ink">
                Nothing meaningful changed
              </h2>
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-muted">
                Your watchlist looks much like it did the last time you checked.
                {data.unchangedCount > 0 && (
                  <> {data.unchangedCount} stock{data.unchangedCount === 1 ? "" : "s"} checked.</>
                )}
              </p>
            </section>
          )}
        </div>
      )}

      {watched !== null && watched > 0 && (
        <section className="flex flex-col gap-3 rounded-xl border border-line bg-card p-5 shadow-card sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="eyebrow">Your watchlist</h2>
            <p className="mt-1 text-[15px] font-medium text-ink">
              {watched} stock{watched === 1 ? "" : "s"} monitored
            </p>
          </div>
          <Link
            to="/watchlist"
            className="btn"
          >
            View watchlist
          </Link>
        </section>
      )}
    </div>
  );
}