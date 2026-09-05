import { Link } from "react-router-dom";
import type { ExploreItem } from "../../domain/types";
import { formatCurrency, formatPercentage } from "../../utils/formatting";
import { DayRangeBar } from "../market/DayRangeBar";

const retTone = (v: number | null) =>
  v === null ? "text-ink" : v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink";

/** A discovery feed row: real snapshot + signal data only. */
export function ExploreRow({ item }: { item: ExploreItem }) {
  const { instrument, snapshot, signal } = item;
  const price = snapshot?.price ?? signal?.currentPrice ?? null;
  const ret = signal?.returnPct ?? null;
  const open = snapshot?.open ?? null;

  return (
    <li>
      <Link
        to={`/stock/${instrument.instrumentId}`}
        className="group flex items-center justify-between gap-4 py-3"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold tracking-tight text-ink group-hover:text-signal-notable">
              {instrument.symbol}
            </span>
            {instrument.sector && (
              <span className="inline-flex items-center rounded-full bg-paper px-2 py-0.5 text-[11px] font-medium text-ink-soft ring-1 ring-inset ring-line">
                {instrument.sector}
              </span>
            )}
          </div>
          <p className="mt-0.5 truncate text-xs text-ink-muted">{instrument.companyName}</p>
          <div className="mt-2.5 max-w-[180px]">
            <DayRangeBar low={snapshot?.low ?? null} high={snapshot?.high ?? null} current={snapshot?.price ?? null} open={open} />
          </div>
        </div>
        <div className="shrink-0 text-right">
          <p className="font-mono text-base font-medium tracking-tight text-ink">
            {formatCurrency(price, instrument.currency)}
          </p>
          {ret !== null && (
            <p className={`mt-0.5 text-sm font-semibold ${retTone(ret)}`}>
              {formatPercentage(ret)}
            </p>
          )}
        </div>
      </Link>
    </li>
  );
}