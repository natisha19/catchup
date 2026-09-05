import type { ReactNode } from "react";
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

function Hint({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-xs leading-relaxed text-ink-muted">{children}</p>;
}

/** Tiny z-score gauge: marker on a −3σ…+3σ track. Explanation-friendly. */
function ZScoreMeter({ zScore }: { zScore: number | null }) {
  if (zScore === null) return null;
  const clamped = Math.max(-3, Math.min(3, zScore));
  const leftPct = ((clamped + 3) / 6) * 100;
  const abs = Math.abs(zScore);
  const tone = abs > 3 ? "bg-down" : abs >= 2 ? "bg-accent" : "bg-up";
  return (
    <div className="mt-1 max-w-[220px]">
      <p className="text-[11px] text-ink-muted">Todays move vs its own history:</p>
      <div className="relative mt-1 h-1.5 rounded-full bg-paper ring-1 ring-inset ring-line">
        <span aria-hidden className="absolute left-1/2 -top-0.5 h-2.5 w-px bg-line" />
        <span
          aria-hidden
          className={`absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full ${tone} ring-2 ring-card`}
          style={{ left: `${leftPct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-ink-muted" aria-hidden>
        <span>−3σ</span>
        <span>0</span>
        <span>+3σ</span>
      </div>
    </div>
  );
}

/** Paired bars: today's volume vs the baseline average, for that ratio in context. */
function VolumeBars({ current, baseline }: { current: number | null; baseline: number | null }) {
  if (current === null || baseline === null) return null;
  const max = Math.max(current, baseline, 1);
  const ratio = current / baseline;
  const currentTone = ratio >= 2 ? "bg-accent" : ratio > 1 ? "bg-up" : "bg-ink-soft";
  const Bar = ({ label, value, tone }: { label: string; value: number; tone: string }) => (
    <div className="flex items-center gap-2">
      <span className="w-14 shrink-0 text-[11px] text-ink-muted">{label}</span>
      <span className={`h-2 rounded-full ${tone}`} style={{ width: `${(value / max) * 100}%` }} />
      <span className="shrink-0 font-mono text-[11px] text-ink-muted">{formatVolume(value)}</span>
    </div>
  );
  return (
    <div className="mt-2 max-w-[260px] space-y-1.5">
      <Bar label="Today" value={current} tone={currentTone} />
      <Bar label="Typical" value={baseline} tone="bg-ink-soft" />
    </div>
  );
}

/**
 * Evidence panel: renders what the backend provides with plain-language hints so
 * raw numbers stay interpretable. No derivation — values come straight from the
 * signal/snapshot the backend computed.
 */
export function RawDataPanel({ detail }: { detail: ChangeDetail }) {
  const s = detail.latestSignal;
  const snap = detail.snapshot;
  return (
    <Collapsible title="Raw data">
      <div className="space-y-4">
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">Signal</h4>
          <RawRow label="Event type" value={s?.eventType ?? "—"} />
          <RawRow label="Previous price" value={formatCurrency(s?.previousPrice ?? null)} />
          <RawRow label="Current price" value={formatCurrency(s?.currentPrice ?? null)} />
          <RawRow label="Return" value={formatPercentage(s?.returnPct ?? null)} />
          <RawRow label="Baseline mean" value={s?.baselineMean?.toString() ?? "—"} />
          <RawRow label="Baseline std" value={s?.baselineStd?.toString() ?? "—"} />
          <ZScoreMeter zScore={s?.zScore ?? null} />
          <RawRow label="Z-score" value={s?.zScore?.toString() ?? "—"} />
          <RawRow label="Current volume" value={formatVolume(s?.currentVolume ?? null)} />
          <RawRow label="Baseline avg volume" value={formatVolume(s?.baselineAverageVolume ?? null)} />
          <RawRow label="Volume ratio" value={s?.volumeRatio?.toString() ?? "—"} />
          <VolumeBars current={s?.currentVolume ?? null} baseline={s?.baselineAverageVolume ?? null} />
          <RawRow label="Data status" value={s?.dataStatus ?? "—"} />
          <RawRow label="Observed at" value={formatTimestamp(s?.observedAt)} />
          <Hint>
            Return compares today&apos;s price with the previous snapshot. The
            baseline is the range of daily moves this stock typically makes;
            the z-score counts how many “typical steps” today&apos;s move is from
            normal (±2 is already uncommon). Volume ratio is today&apos;s volume
            divided by the stock&apos;s usual average — 2× means double the trading.
            Data status tells you how fresh the numbers are.
          </Hint>
        </div>
        {snap && (
          <div>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">Snapshot</h4>
            <RawRow label="Source" value={snap.source} />
            <RawRow label="Observed at" value={formatTimestamp(snap.observedAt)} />
            <RawRow label="Received at" value={formatTimestamp(snap.receivedAt ?? null)} />
            <RawRow label="Open / High / Low" value={`${snap.open ?? "—"} / ${snap.high ?? "—"} / ${snap.low ?? "—"}`} />
            <RawRow label="Volume" value={formatVolume(snap.volume ?? null)} />
            <RawRow label="Data status" value={snap.dataStatus} />
            <Hint>
              The last market data point the ingestion pipeline wrote: the
              provider it came from, when it was observed, and the day&apos;s range
              so far.
            </Hint>
          </div>
        )}
      </div>
    </Collapsible>
  );
}