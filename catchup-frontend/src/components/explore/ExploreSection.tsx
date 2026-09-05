import type { ExploreItem } from "../../domain/types";
import { ExploreRow } from "./ExploreRow";

export function ExploreSection({
  id,
  title,
  hint,
  items,
  sector,
}: {
  id: string;
  title: string;
  hint: string;
  items: ExploreItem[];
  /** Sector the whole page is scoped to (copies only); null = All. */
  sector: string | null;
}) {
  return (
    <section aria-labelledby={id} className="card p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id={id} className="eyebrow">{title}</h2>
        <span className="shrink-0 text-xs text-ink-muted">{hint}</span>
      </div>
      {items.length > 0 ? (
        <ul className="mt-2 divide-y divide-line">
          {items.map((item) => (
            <ExploreRow key={item.instrument.instrumentId} item={item} />
          ))}
        </ul>
      ) : (
        <p className="mt-3 rounded-lg bg-paper px-3 py-6 text-center text-xs text-ink-muted">
          {sector
            ? `No ${sector} stocks have valid data in this list yet.`
            : "Awaiting first market data."}
        </p>
      )}
    </section>
  );
}