import type { CatchupFeed } from "../../domain/types";
import { formatTimeOnly } from "../../utils/date";

const statusConfig = {
  OPEN: { dot: "bg-up", label: "Market open", hint: "Live session in progress" },
  CLOSED: { dot: "bg-ink-muted", label: "Market closed", hint: "Stock exchanges are not trading" },
  UNKNOWN: { dot: "bg-ink-muted/50", label: "Market status unknown", hint: "" },
} as const;

export function MarketStatusBanner({ feed }: { feed: CatchupFeed }) {
  const config = statusConfig[feed.marketStatus];
  return (
    <div
      role="status"
      className="card flex flex-row items-center justify-between gap-x-6 gap-y-1 px-4 py-3.5 sm:px-5"
    >
      <span className="flex items-center gap-2.5">
        <span aria-hidden className={`h-2 w-2 rounded-full ${config.dot}`} />
        <span className="font-semibold text-ink">{config.label}</span>
      </span>
      <span className="shrink-0 text-right text-sm text-ink-muted">
        {feed.marketStatus === "CLOSED" && feed.lastMarketSessionAt ? (
          <>
            Last session{" "}
            <span className="font-semibold text-ink">
              {formatTimeOnly(feed.lastMarketSessionAt)}
            </span>
          </>
        ) : (
          config.hint
        )}
      </span>
    </div>
  );
}