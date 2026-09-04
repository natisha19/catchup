import { Link, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { SnapshotHeader } from "../components/market/SnapshotHeader";
import { WhyPanel } from "../components/catchup/WhyPanel";
import { RawDataPanel } from "../components/catchup/RawDataPanel";
import { ChangeCard } from "../components/catchup/ChangeCard";
import { formatLastChecked } from "../utils/date";
import { getMarketStatus, rememberMarketStatus } from "../domain/marketStatusCache";

export function StockDetailPage() {
  const { instrumentId = "" } = useParams();
  const { catchup } = useApis();
  const detail = useAsync(() => catchup.getInstrumentChange(instrumentId), [instrumentId]);
  // Market status is not part of the snapshot payload; reuse the existing feed
  // so the freshness label can distinguish "market closed + latest session"
  // from genuinely stale data. Fall back to the cached status so "Latest
  // session data" never flickers to "Stale data" while the feed is resolving.
  const feed = useAsync(() => catchup.getFeed(), []);

  const resolvedFeed = feed.status === "success" ? feed.data : null;
  useEffect(() => {
    if (resolvedFeed) rememberMarketStatus(resolvedFeed.marketStatus);
  }, [resolvedFeed]);

  if (detail.status === "loading") return (
    <div className="flex min-h-[40vh] items-center justify-center"><Spinner label="Loading stock" /></div>
  );
  if (detail.status === "error") {
    return <ErrorState title="Could not load this stock" message={detail.error.message} onRetry={detail.reload} />;
  }

  const { data } = detail;
  const s = data.latestSignal;
  const marketStatus =
    feed.status === "success" ? feed.data.marketStatus : getMarketStatus();

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink">
        <span aria-hidden>←</span> Back to feed
      </Link>

      <SnapshotHeader
        detail={data}
        currency={data.instrument.currency}
        marketStatus={marketStatus}
      />

      {s && s.observedAt && (
        <p className="text-sm text-ink-muted">You last checked {formatLastChecked(s.observedAt)}.</p>
      )}

      {s ? (
        <>
          <section aria-labelledby="changed-heading" className="card p-5">
            <h2 id="changed-heading" className="eyebrow">
              What changed?
            </h2>
            <p className="mt-2 text-lg font-medium text-ink">{s.eventDescription}</p>
          </section>
          <WhyPanel signal={s} />
        </>
      ) : (
        <section className="card p-5">
          <h2 className="eyebrow">What changed?</h2>
          <p className="mt-2 text-sm text-ink-muted">No significant changes since you last checked.</p>
        </section>
      )}

      {data.otherSignals.length > 0 && (
        <section>
          <h2 className="mb-3 eyebrow">Other changes</h2>
          <div className="space-y-4">
            {data.otherSignals.map((sig) => (
              <ChangeCard key={sig.id} signal={sig} marketStatus={marketStatus} />
            ))}
          </div>
        </section>
      )}

      <RawDataPanel detail={data} />
    </div>
  );
}