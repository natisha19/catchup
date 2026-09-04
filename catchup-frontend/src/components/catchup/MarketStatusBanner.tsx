import type { CatchupFeed } from "../../domain/types";
import { formatTimeOnly } from "../../utils/date";

export function MarketStatusBanner({ feed }: { feed: CatchupFeed }) {
  if (feed.marketStatus !== "CLOSED") return null;
  return (
    <div
      role="status"
      className="mb-6 rounded-lg border border-line bg-white px-4 py-3 text-sm text-ink-soft"
    >
      <span className="font-medium text-ink">Market closed.</span>{" "}
      Last market session: {formatTimeOnly(feed.lastMarketSessionAt)}
    </div>
  );
}
