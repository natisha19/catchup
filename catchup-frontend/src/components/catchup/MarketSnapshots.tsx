import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { ChangeDetail, DataStatus, MarketStatus, WatchlistItem } from "../../domain/types";
import { useApis } from "../../hooks/useApis";
import { DataStatusBadge } from "../common/DataStatusBadge";
import { formatCurrency, formatPercentage } from "../../utils/formatting";

const REFRESH_SECONDS = 30;

interface WatchedRow {
  item: WatchlistItem;
  detail: ChangeDetail | null;
}

function priceOf(detail: ChangeDetail | null): number | null {
  if (!detail) return null;
  return detail.snapshot?.price ?? detail.latestSignal?.currentPrice ?? null;
}

function returnOf(detail: ChangeDetail | null): number | null {
  return detail?.latestSignal?.returnPct ?? null;
}

function statusOf(detail: ChangeDetail | null): DataStatus | null {
  if (!detail) return null;
  return detail.snapshot?.dataStatus ?? detail.latestSignal?.dataStatus ?? null;
}

const tone = (v: number) => (v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink");
const arrow = (v: number) => (v > 0 ? "▲" : v < 0 ? "▼" : "·");

/**
 * A real-data snapshot of the user's watchlist, fetched through one batched
 * endpoint (never fabricated, never hard-coded).
 *
 * Every watched stock is shown — including freshly added ones that have no
 * baseline yet — so the feed is useful even when nothing "meaningfully
 * changed". Leaderboards (top performers / biggest dips) are derived from the
 * same real return percentages, so they are empty when there is no data to
 * show rather than pretending.
 */
export function MarketSnapshots({
  items,
  marketStatus,
}: {
  items: WatchlistItem[];
  marketStatus?: MarketStatus;
}) {
  const { watchlist } = useApis();
  const [rows, setRows] = useState<Record<string, ChangeDetail | null | undefined>>({});
  const [secondsLeft, setSecondsLeft] = useState(REFRESH_SECONDS);
  const [refreshToken, setRefreshToken] = useState(0);

  const uniqueItems = useMemo(() => {
    const seen = new Set<string>();
    return items.filter(({ instrument }) => {
      if (seen.has(instrument.instrumentId)) return false;
      seen.add(instrument.instrumentId);
      return true;
    });
  }, [items]);

  const fetchAll = useCallback(() => {
    setRefreshToken((t) => t + 1);
    setSecondsLeft(REFRESH_SECONDS);
  }, []);

  useEffect(() => {
    let cancelled = false;
    watchlist.getMarketSnapshots()
      .then((details) => {
        if (cancelled) return;
        setRows(Object.fromEntries(details.map((detail) => [detail.instrument.instrumentId, detail])));
      })
      .catch(() => {
        if (!cancelled) setRows({});
      });
    return () => {
      cancelled = true;
    };
  }, [watchlist, uniqueItems, refreshToken]);

  // Auto-refresh: newly added stocks pick up their first snapshot when the
  // ingestion worker ticks, without reloading the page.
  useEffect(() => {
    if (uniqueItems.length === 0) return;
    const interval = window.setInterval(() => {
      setSecondsLeft((s) => s - 1);
    }, 1000);
    const onFocus = () => fetchAll();
    const onVisibility = () => {
      if (document.visibilityState === "visible") fetchAll();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [uniqueItems, fetchAll]);

  useEffect(() => {
    if (secondsLeft > 0) return;
    setRefreshToken((t) => t + 1);
    setSecondsLeft(REFRESH_SECONDS);
  }, [secondsLeft]);

  const watched: WatchedRow[] = uniqueItems.map((item) => ({
    item,
    detail: rows[item.instrument.instrumentId] ?? null,
  }));

  const leaders = watched
    .map((w) => ({ w, ret: returnOf(w.detail) }))
    .filter((x): x is { w: WatchedRow; ret: number } => x.ret !== null && x.ret !== 0);
  const gainers = [...leaders].filter((x) => x.ret > 0).sort((a, b) => b.ret - a.ret).slice(0, 4);
  const dippers = [...leaders].filter((x) => x.ret < 0).sort((a, b) => a.ret - b.ret).slice(0, 4);

  return (
    <section aria-labelledby="watchlist-today-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="watchlist-today-heading" className="eyebrow">
            Watchlist today
          </h2>
<p className="mt-1 text-[15px] font-medium text-ink">
          {uniqueItems.length} stock{uniqueItems.length === 1 ? "" : "s"} monitored — latest prices and moves.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-ink-muted" aria-live="polite">
          Refreshing in {secondsLeft}s
        </span>
        <button
          type="button"
          className="btn px-3 py-1.5 text-xs"
          onClick={fetchAll}
        >
          Refresh now
        </button>
        <Link to="/watchlist?add=1" className="btn px-3 py-1.5 text-xs">
          Add a stock
        </Link>
      </div>
    </div>

      <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {watched.map(({ item, detail }) => {
          const { instrument, baselineStatus } = item;
          const price = priceOf(detail);
          const ret = returnOf(detail);
          const status = statusOf(detail);
          return (
            <li key={instrument.instrumentId}>
              <Link
                to={`/stock/${instrument.instrumentId}`}
                className="card flex h-full flex-col p-4 transition-shadow hover:shadow-raised"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold tracking-tight text-ink">
                    {instrument.symbol}
                  </span>
                  {status && <DataStatusBadge status={status} marketStatus={marketStatus} />}
                </div>
                <span className="mt-0.5 truncate text-xs text-ink-muted">
                  {instrument.companyName}
                </span>
                <span className="mt-3 font-mono text-lg font-medium tracking-tight text-ink">
                  {price !== null ? formatCurrency(price, instrument.currency) : "—"}
                </span>
                {ret !== null ? (
                  <span className={`mt-0.5 text-sm font-semibold ${tone(ret)}`}>
                    <span aria-hidden>{arrow(ret)}</span> {formatPercentage(ret)}
                  </span>
                ) : price !== null ? (
                  baselineStatus === "INSUFFICIENT" ? (
                    <span className="mt-1 text-xs font-medium text-signal-significant">
                      Baseline being established.
                    </span>
                  ) : (
                    <span className="mt-1 text-xs text-ink-muted">No change yet.</span>
                  )
                ) : (
                  <span className="mt-1 text-xs text-ink-muted">
                    Awaiting first market data · auto-refreshing
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>

      {(gainers.length > 0 || dippers.length > 0) && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {gainers.length > 0 && (
            <section aria-label="Top performers" className="card p-4">
              <h3 className="eyebrow">Top performers</h3>
              <ul className="mt-3 space-y-2.5">
                {gainers.map(({ w, ret }) => (
                  <LeaderRow key={w.item.instrument.instrumentId} row={w} ret={ret} />
                ))}
              </ul>
            </section>
          )}
          {dippers.length > 0 && (
            <section aria-label="Biggest dips" className="card p-4">
              <h3 className="eyebrow">Biggest dips</h3>
              <ul className="mt-3 space-y-2.5">
                {dippers.map(({ w, ret }) => (
                  <LeaderRow key={w.item.instrument.instrumentId} row={w} ret={ret} />
                ))}
              </ul>
            </section>
          )}
        </div>
      )}

      <p className="mt-5 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-ink-muted">
        <span>Looking for a stock you don&apos;t watch yet?</span>
        <Link to="/watchlist?add=1" className="font-medium text-signal-notable hover:underline">
          Search the catalog and add it
        </Link>
      </p>
    </section>
  );
}

function LeaderRow({ row, ret }: { row: WatchedRow; ret: number }) {
  const { item } = row;
  return (
    <li>
      <Link
        to={`/stock/${item.instrument.instrumentId}`}
        className="group flex items-center justify-between gap-3"
      >
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium text-ink group-hover:text-signal-notable">
            {item.instrument.symbol}
          </span>
          <span className="block truncate text-xs text-ink-muted">
            {item.instrument.companyName}
          </span>
        </span>
        <span className={`shrink-0 text-sm font-semibold ${tone(ret)}`}>
          {formatPercentage(ret)}
        </span>
      </Link>
    </li>
  );
}
