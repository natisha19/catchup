import { Link, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { SnapshotHeader } from "../components/market/SnapshotHeader";
import { DayRangeBar } from "../components/market/DayRangeBar";
import { WhyPanel } from "../components/catchup/WhyPanel";
import { RawDataPanel } from "../components/catchup/RawDataPanel";
import { ChangeCard } from "../components/catchup/ChangeCard";
import { formatLastChecked } from "../utils/date";
import { rememberMarketStatus } from "../domain/marketStatusCache";

export function StockDetailPage() {
  const { instrumentId = "" } = useParams();
  const { catchup } = useApis();
  const detail = useAsync(() => catchup.getInstrumentChange(instrumentId), [instrumentId]);

  const resolved = detail.status === "success" ? detail.data : null;
  // The detail now carries its own per-exchange status (spec §16); remember it
  // app-wide so the freshness label never flickers between statuses.
  const marketStatus = resolved?.marketStatus ?? undefined;
  useEffect(() => {
    if (marketStatus) rememberMarketStatus(marketStatus);
  }, [marketStatus]);

  if (detail.status === "loading") return (
    <div className="flex min-h-[40vh] items-center justify-center"><Spinner label="Loading stock" /></div>
  );
  if (detail.status === "error") {
    return <ErrorState title="Could not load this stock" message={detail.error.message} onRetry={detail.reload} />;
  }

  const { data } = detail;
  const s = data.latestSignal;
  const snap = data.snapshot;
  const previousPrice = s?.previousPrice ?? data.previousSeenPrice ?? null;

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink">
        <span aria-hidden>←</span> Back to explore
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
            {s.reasonCodes.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {s.reasonCodes.map((r) => (
                  <span
                    key={r}
                    className="inline-flex items-center rounded-full bg-paper px-2.5 py-0.5 text-[11px] font-medium text-ink-soft ring-1 ring-inset ring-line"
                  >
                    {r.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            )}
            {snap?.high != null && snap.low != null && snap.price != null && (
              <div className="mt-4 max-w-xs">
                <p className="mb-1.5 text-xs text-ink-muted">Where the day&apos;s range sits — real snapshot:</p>
                <DayRangeBar low={snap.low} high={snap.high} current={snap.price} open={snap.open ?? null} />
              </div>
            )}
          </section>
          <WhyPanel signal={s} />
        </>
      ) : (
        <section className="card p-5">
          <h2 className="eyebrow">What changed?</h2>
          <p className="mt-2 text-sm text-ink-muted">
            {previousPrice !== null
              ? "No significant changes since you last checked."
              : "Baseline being established. Catchup will remember today's snapshot for next time."}
          </p>
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