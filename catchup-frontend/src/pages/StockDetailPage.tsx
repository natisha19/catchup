import { Link, useParams } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { useApis } from "../hooks/useApis";
import { Spinner } from "../components/common/Spinner";
import { ErrorState } from "../components/common/ErrorState";
import { SnapshotHeader } from "../components/market/SnapshotHeader";
import { WhyPanel } from "../components/catchup/WhyPanel";
import { RawDataPanel } from "../components/catchup/RawDataPanel";
import { ChangeCard } from "../components/catchup/ChangeCard";
import { formatLastChecked } from "../utils/date";

export function StockDetailPage() {
  const { instrumentId = "" } = useParams();
  const { catchup } = useApis();
  const detail = useAsync(() => catchup.getInstrumentChange(instrumentId), [instrumentId]);

  if (detail.status === "loading") return <div className="py-16"><Spinner label="Loading stock" /></div>;
  if (detail.status === "error") {
    return <ErrorState title="Could not load this stock" message={detail.error.message} onRetry={detail.reload} />;
  }

  const { data } = detail;
  const s = data.latestSignal;

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-ink-muted hover:text-ink">← Back to feed</Link>
      <SnapshotHeader detail={data} currency={data.instrument.currency} />

      {s && s.observedAt && (
        <p className="text-sm text-ink-muted">You last checked {formatLastChecked(s.observedAt)}.</p>
      )}

      {s ? (
        <>
          <section aria-labelledby="changed-heading" className="rounded-lg border border-line bg-white p-5">
            <h2 id="changed-heading" className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
              What changed?
            </h2>
            <p className="mt-2 text-lg font-medium">{s.eventDescription}</p>
          </section>
          <WhyPanel signal={s} />
        </>
      ) : (
        <section className="rounded-lg border border-line bg-white p-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">What changed?</h2>
          <p className="mt-2 text-sm text-ink-muted">No significant changes since you last checked.</p>
        </section>
      )}

      {data.otherSignals.length > 0 && (
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">Other changes</h2>
          <div className="space-y-4">
            {data.otherSignals.map((sig) => <ChangeCard key={sig.id} signal={sig} />)}
          </div>
        </section>
      )}

      <RawDataPanel detail={data} />
    </div>
  );
}
