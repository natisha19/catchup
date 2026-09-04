import type { CatchupFeed } from "../../domain/types";
import { formatTimeOnly } from "../../utils/date";

const statusConfig = {
  OPEN: { dot: "bg-up", label: "Market open" },
  CLOSED: { dot: "bg-ink-muted", label: "Market closed" },
  UNKNOWN: { dot: "bg-ink-muted/50", label: "Market status unknown" },
} as const;

export function MarketStatusBanner({ feed }: { feed: CatchupFeed }) {
  const config = statusConfig[feed.marketStatus];
  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1 rounded-lg border border-line bg-card px-4 py-3 text-sm shadow-card"
    >
      <span className="flex items-center gap-2.5 font-medium text-ink">
        <span aria-hidden className={`h-2 w-2 rounded-full ${config.dot}`} />
        {config.label}
      </span>
      {feed.marketStatus === "CLOSED" && feed.lastMarketSessionAt && (
        <span className="text-ink-muted">
          Last session{" "}
          <span className="font-medium text-ink-soft">
            {formatTimeOnly(feed.lastMarketSessionAt)}
          </span>
        </span>
      )}
    </div>
  );
}