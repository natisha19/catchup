import type { ChangeDetail } from "../../domain/types";
import { DataStatusBadge } from "../common/DataStatusBadge";
import {
  formatCurrency, formatPercentage, formatSignedCurrency,
} from "../../utils/formatting";
import { formatLastChecked } from "../../utils/date";

export function SnapshotHeader({
  detail,
  currency,
}: {
  detail: ChangeDetail;
  currency: string;
}) {
  const { instrument, snapshot, latestSignal } = detail;
  const price = snapshot?.price ?? latestSignal?.currentPrice ?? null;
  const ret = latestSignal?.returnPct ?? null;
  const tone = ret === null ? "text-ink" : ret >= 0 ? "text-up" : "text-down";

  if (snapshot?.dataStatus === "UNAVAILABLE" && price === null) {
    return (
      <div role="status" className="card p-5">
        <h1 className="text-2xl font-bold text-ink">{instrument.symbol}</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Market data temporarily unavailable.{" "}
          {snapshot && snapshot.observedAt && (
            <>Showing last known data from {formatLastChecked(snapshot.observedAt)}.</>
          )}
        </p>
      </div>
    );
  }

  return (
    <div className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold text-ink">{instrument.symbol}</h1>
            <span className="inline-flex items-center rounded-full bg-paper px-2 py-0.5 text-[11px] font-medium text-ink-soft ring-1 ring-inset ring-line">
              {instrument.exchange}
            </span>
          </div>
          <p className="mt-1 text-sm text-ink-muted">{instrument.companyName}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-medium tracking-tight text-ink sm:text-3xl">
            {formatCurrency(price, currency)}
          </p>
          {ret !== null && (
            <p className={`mt-0.5 text-sm font-semibold ${tone}`}>
              {formatPercentage(ret)}
            </p>
          )}
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2.5">
        {snapshot && <DataStatusBadge status={snapshot.dataStatus} />}
        {snapshot?.dataStatus === "STALE" && (
          <span className="text-xs text-ink-muted">
            Last updated {formatLastChecked(snapshot.observedAt)}
          </span>
        )}
      </div>
      {detail.previousSeenPrice !== null && price !== null && (
        <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-line pt-4 text-sm">
          <div>
            <dt className="eyebrow">You last saw</dt>
            <dd className="mt-1 font-mono text-ink">{formatCurrency(detail.previousSeenPrice, currency)}</dd>
          </div>
          <div>
            <dt className="eyebrow">Now</dt>
            <dd className="mt-1 font-mono text-ink">{formatCurrency(price, currency)}</dd>
          </div>
          <div>
            <dt className="eyebrow">Change</dt>
            <dd className={`mt-1 font-mono ${tone}`}>
              {formatSignedCurrency(price - detail.previousSeenPrice, currency)}{" "}
              ({formatPercentage(ret)})
            </dd>
          </div>
        </dl>
      )}
      {detail.previousSeenPrice === null && (
        <p className="mt-4 border-t border-line pt-3 text-sm font-medium text-signal-significant">
          Baseline being established. Catchup will remember this price for next time.
        </p>
      )}
    </div>
  );
}