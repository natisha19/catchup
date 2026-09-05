/**
 * Informational empty-watchlist state. The single clear primary "Add a stock"
 * lives in the page header (sticky, always visible), so this area intentionally
 * has no duplicate CTA.
 */
export function EmptyWatchlist() {
  return (
    <section className="card flex flex-col items-center px-6 py-14 text-center">
      <span
        aria-hidden
        className="flex h-12 w-12 items-center justify-center rounded-full bg-paper text-ink-muted ring-1 ring-inset ring-line"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 5v14M5 12h14"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </span>
      <h2 className="mt-5 text-xl font-semibold text-ink">Your watchlist is empty.</h2>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-muted">
        Add stocks you want Catchup to remember.
      </p>
    </section>
  );
}