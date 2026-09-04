import { Link } from "react-router-dom";

export function FirstVisitNotice({ hasWatchlist }: { hasWatchlist: boolean }) {
  return (
    <section className="card flex flex-col items-center px-6 py-12 text-center sm:py-14">
      <span
        aria-hidden
        className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
          <circle cx="12" cy="12" r="3" fill="currentColor" />
        </svg>
      </span>
      <h2 className="mt-5 text-xl font-semibold text-ink">Welcome to Catchup.</h2>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-muted">
        {hasWatchlist
          ? "Catchup will remember today's snapshot. When you return, it will show you what changed."
          : "Add stocks to your watchlist. When you return, Catchup will show you what changed."}
      </p>
      {!hasWatchlist && (
        <Link to="/watchlist" className="btn-primary mt-6">
          Add a stock
        </Link>
      )}
    </section>
  );
}