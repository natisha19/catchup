import type { ChangeDetail } from "../../domain/types";
import { Collapsible } from "../common/Collapsible";
import {
  formatCurrency, formatPercentage, formatVolume,
} from "../../utils/formatting";
import { formatTimestamp } from "../../utils/date";

function RawRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1 text-sm font-mono">
      <span className="text-ink-muted">{label}</span>
      <span className="text-right text-ink">{value}</span>
    </div>
  );
}

/** Evidence panel: renders what the backend provides. No derivation. */
export function RawDataPanel({ detail }: { detail: ChangeDetail }) {
  const s = detail.latestSignal;
  const snap = detail.snapshot;
  return (
    <Collapsible title="Raw data">
      <div className="space-y-4">
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">Signal</h4>
          <RawRow label="Event type" value={s?.eventType ?? "—"} />
          <RawRow label="Previous price" value={formatCurrency(s?.previousPrice ?? null)} />
          <RawRow label="Current price" value={formatCurrency(s?.currentPrice ?? null)} />
          <RawRow label="Return" value={formatPercentage(s?.returnPct ?? null)} />
          <RawRow label="Baseline mean" value={s?.baselineMean?.toString() ?? "—"} />
          <RawRow label="Baseline std" value={s?.baselineStd?.toString() ?? "—"} />
          <RawRow label="Z-score" value={s?.zScore?.toString() ?? "—"} />
          <RawRow label="Current volume" value={formatVolume(s?.currentVolume ?? null)} />
          <RawRow label="Baseline avg volume" value={formatVolume(s?.baselineAverageVolume ?? null)} />
          <RawRow label="Volume ratio" value={s?.volumeRatio?.toString() ?? "—"} />
          <RawRow label="Data status" value={s?.dataStatus ?? "—"} />
          <RawRow label="Observed at" value={formatTimestamp(s?.observedAt)} />
        </div>
        {snap && (
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">Snapshot</h4>
            <RawRow label="Source" value={snap.source} />
            <RawRow label="Observed at" value={formatTimestamp(snap.observedAt)} />
            <RawRow label="Received at" value={formatTimestamp(snap.receivedAt ?? null)} />
            <RawRow label="Open / High / Low" value={`${snap.open ?? "—"} / ${snap.high ?? "—"} / ${snap.low ?? "—"}`} />
            <RawRow label="Volume" value={formatVolume(snap.volume ?? null)} />
            <RawRow label="Data status" value={snap.dataStatus} />
          </div>
        )}
      </div>
    </Collapsible>
  );
}