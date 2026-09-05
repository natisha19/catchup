import { useState } from "react";
import { Link } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { useAddInstrument } from "../hooks/useAddInstrument";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { SearchBox } from "../components/search/SearchBox";
import { ExploreSection } from "../components/explore/ExploreSection";

export function ExplorePage() {
  const { explore, watchlist, instrument } = useApis();
  const [query, setQuery] = useState("");
  const [activeSector, setActiveSector] = useState<string | null>(null);

  // The sector chip scopes the backend query genuinely: each change triggers one
  // refetch of the entire feed for that sector (never a client-side re-filter,
  // never N+1 requests). The backend keeps the sectors breadcrumbs stable.
  const feed = useAsync(
    () => explore.getExplore(undefined, activeSector ?? undefined),
    [activeSector],
  );
  const list = useAsync(() => watchlist.getWatchlist(), []);
  const add = useAddInstrument(watchlist);
  const search = useAsync(
    () => query.trim() ? instrument.search(query.trim()) : Promise.resolve([]),
    [query],
  );

  const watchedItems = list.status === "success" ? list.data.items : [];
  const watchedIds = new Set(watchedItems.map((i) => i.instrument.instrumentId));

  const data = feed.status === "success" ? feed.data : null;
  const hasAny =
    (data?.movers.length ?? 0) + (data?.dippers.length ?? 0) + (data?.unusual.length ?? 0) > 0;

  return (
    <div className="space-y-10">
      <header className="max-w-2xl">
        <p className="eyebrow">Explore</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          Find what&apos;s moving in the market.
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          Real movers, dips, and unusual activity across the discovery universe —
          stocks you may not be watching yet. Data comes from the same ingestion
          pipeline that powers your watchlist.
        </p>
      </header>

      <section className="card p-5 sm:p-6" aria-label="Search the catalog">
        <h2 className="eyebrow">Search the catalog</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Find a stock by symbol or company. Stocks already in your watchlist
          are filtered out so you only see new additions.
        </p>
        <div className="mt-3">
          <SearchBox
            query={query}
            onQueryChange={setQuery}
            results={search.status === "success" ? search.data : []}
            loading={search.status === "loading"}
            error={search.status === "error" ? search.error.message : null}
            onRetry={() => void search.reload()}
            watchedIds={watchedIds}
            addingId={add.addingId}
            addedIds={add.added}
            failed={add.failed}
            onAddInstrument={add.addInstrument}
            onAddSymbol={add.addBySymbol}
            onRetryAdd={add.retry}
            ariaLabel="Search all instruments"
          />
        </div>
      </section>

      <section aria-labelledby="market-movers-heading" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="market-movers-heading" className="eyebrow">Market movers</h2>
            <p className="mt-1 text-sm text-ink-muted">
              {activeSector
                ? `${activeSector}, latest session.`
                : "Across the discovery universe, latest session."}
            </p>
          </div>
          {data && data.sectors.length > 1 && (
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by sector">
              <button
                type="button"
                onClick={() => setActiveSector(null)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  activeSector === null
                    ? "border-signal-notable bg-paper text-signal-notable"
                    : "border-line bg-card text-ink-soft hover:text-ink"
                }`}
              >
                All
              </button>
              {data.sectors.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setActiveSector((cur) => (cur === s ? null : s))}
                  aria-pressed={activeSector === s}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                    activeSector === s
                      ? "border-signal-notable bg-paper text-signal-notable"
                      : "border-line bg-card text-ink-soft hover:text-ink"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {feed.status === "loading" && (
          <div className="py-8"><Spinner label="Loading market movers" /></div>
        )}
        {feed.status === "error" && (
          <ErrorState
            title="Could not load market movers"
            message={feed.error.message}
            onRetry={feed.reload}
          />
        )}
        {feed.status === "success" && !hasAny && (
          <div className="card px-6 py-12 text-center">
            <p className="text-sm text-ink-muted">
              {activeSector ? (
                <>
                  No {activeSector} stocks have valid market data right now. Movers
                  appear once a trading session writes snapshots for that sector.
                </>
              ) : (
                <>
                  Awaiting first market data — movers appear once a trading session
                  writes snapshots for the discovery universe.
                </>
              )}
            </p>
          </div>
        )}
        {feed.status === "success" && hasAny && data && (
          <div className="grid gap-6 lg:grid-cols-3">
            <ExploreSection id="movers-heading" title="Top movers" hint="Biggest gains" items={data.movers} sector={activeSector} />
            <ExploreSection id="dippers-heading" title="Dippers" hint="Biggest losses" items={data.dippers} sector={activeSector} />
            <ExploreSection id="unusual-heading" title="Unusual activity" hint="Volume & z-score outliers" items={data.unusual} sector={activeSector} />
          </div>
        )}
      </section>

      {list.status === "success" && watchedItems.length === 0 && (
        <section className="card flex flex-col items-start p-5 sm:p-6">
          <h2 className="eyebrow">Explorers start with a blank watchlist</h2>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-ink-muted">
            Catchup remembers what your watchlist looked like when you last
            checked, then shows you what changed. Add a stock from anywhere —
            the search above, or the Watchlist page.
          </p>
          <Link to="/watchlist" className="btn mt-4">
            Go to your watchlist
          </Link>
        </section>
      )}
    </div>
  );
}