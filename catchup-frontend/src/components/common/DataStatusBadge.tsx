import type { DataStatus, MarketStatus } from "../../domain/types";

const styles: Record<DataStatus, string> = {
  LIVE: "bg-upsoft text-up ring-1 ring-inset ring-upline",
  DELAYED: "bg-accent-soft text-signal-significant ring-1 ring-inset ring-accent-line",
  STALE: "bg-paper text-ink-soft ring-1 ring-inset ring-line",
  UNAVAILABLE: "bg-paper text-ink-muted ring-1 ring-inset ring-line",
};

const dot: Record<DataStatus, string> = {
  LIVE: "bg-up",
  DELAYED: "bg-accent",
  STALE: "bg-ink-muted/60",
  UNAVAILABLE: "bg-ink-muted/40",
};

const labels: Record<DataStatus, string> = {
  LIVE: "Live", DELAYED: "Delayed", STALE: "Stale data", UNAVAILABLE: "Unavailable",
};

/**
 * A data-status pill with optional market context.
 *
 * When the market is closed, the most recent valid observation comes from the
 * last completed session — by construction it is older than the backend's
 * recency thresholds. Presenting that as alarming "Stale data" is misleading:
 * the datum is the latest available session data, not broken. The backend's
 * status is never redefined — the label is reinterpreted only when the market
 * state clearly explains it, and the raw status remains visible in Raw Data.
 */
export function DataStatusBadge({
  status,
  marketStatus,
}: {
  status: DataStatus;
  marketStatus?: MarketStatus;
}) {
  const latestSession = status === "STALE" && marketStatus === "CLOSED";
  return (
    <span
      role="status"
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}
    >
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${dot[status]}`} />
      {latestSession ? "Latest session data" : labels[status]}
    </span>
  );
}