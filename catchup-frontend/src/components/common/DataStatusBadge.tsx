import type { DataStatus } from "../../domain/types";

const styles: Record<DataStatus, string> = {
  LIVE: "bg-green-50 text-up border border-green-200",
  DELAYED: "bg-amber-50 text-signal-significant border border-amber-200",
  STALE: "bg-gray-100 text-ink-soft border border-line",
  UNAVAILABLE: "bg-gray-100 text-ink-muted border border-line",
};

const labels: Record<DataStatus, string> = {
  LIVE: "Live", DELAYED: "Delayed", STALE: "Stale data", UNAVAILABLE: "Unavailable",
};

export function DataStatusBadge({ status }: { status: DataStatus }) {
  return (
    <span role="status" className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}
