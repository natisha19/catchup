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

  if (snapshot?.dataStatus === "UNAVAILABLE" && price === null) {
    return (
      <div role="status" className="rounded-lg border border-line bg-white p-5">
        <h1 className="text-2xl font-bold">{instrument.symbol}</h1>
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
    <div className="rounded-lg border border-line bg-white p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{instrument.symbol}</h1>
          <p className="text-sm text-ink-muted">{instrument.companyName}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl">{formatCurrency(price, currency)}</p>
          {ret !== null && (
            <p className={ret >= 0 ? "font-medium text-up" : "font-medium text-down"}>
              {formatPercentage(ret)}
            </p>
          )}
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        {snapshot && <DataStatusBadge status={snapshot.dataStatus} />}
        {snapshot?.dataStatus === "STALE" && (
          <span className="text-xs text-ink-muted">
            Last updated {formatLastChecked(snapshot.observedAt)}
          </span>
        )}
      </div>
      {detail.previousSeenPrice !== null && price !== null && (
        <dl className="mt-4 grid grid-cols-3 gap-2 border-t border-line pt-3 text-sm">
          <div>
            <dt className="text-ink-muted">You last saw</dt>
            <dd className="font-mono">{formatCurrency(detail.previousSeenPrice, currency)}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Now</dt>
            <dd className="font-mono">{formatCurrency(price, currency)}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Change</dt>
            <dd className="font-mono">
              {formatSignedCurrency(price - detail.previousSeenPrice, currency)}{" "}
              ({formatPercentage(ret)})
            </dd>
          </div>
        </dl>
      )}
      {detail.previousSeenPrice === null && (
        <p className="mt-3 border-t border-line pt-3 text-sm italic text-signal-significant">
          Baseline being established. Catchup will remember this price for next time.
        </p>
      )}
    </div>
  );
}
