import { Link } from "react-router-dom";

/**
 * Compact first-visit welcome. Shown only while a fresh user has no baseline
 * yet. One clear primary action ("Add a stock") lives in the page header, so
 * this box deliberately offers no duplicate CTA — just a quiet path to Explore.
 */
export function FirstVisitNotice({ hasWatchlist }: { hasWatchlist: boolean }) {
  return (
    <section className="card flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3 sm:items-center">
        <span
          aria-hidden
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent sm:mt-0"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden>
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
            <circle cx="12" cy="12" r="3" fill="currentColor" />
          </svg>
        </span>
        <div>
          <h2 className="text-[15px] font-semibold text-ink">Welcome to Catchup.</h2>
          <p className="mt-0.5 text-sm leading-relaxed text-ink-muted">
            {hasWatchlist
              ? "Catchup will remember today's snapshot. When you return, it will show you what changed."
              : "Add stocks above — when you return, Catchup shows you what changed."}
          </p>
        </div>
      </div>
      {!hasWatchlist && (
        <Link
          to="/"
          className="shrink-0 text-sm font-medium text-ink-soft transition-colors hover:text-ink sm:pl-4"
        >
          Explore stocks →
        </Link>
      )}
    </section>
  );
}