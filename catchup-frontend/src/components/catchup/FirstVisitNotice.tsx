import { Link } from "react-router-dom";

export function FirstVisitNotice({ hasWatchlist }: { hasWatchlist: boolean }) {
  return (
    <section className="rounded-lg border border-line bg-white p-8 text-center">
      <h2 className="text-xl font-semibold">Welcome to Catchup.</h2>
      <p className="mt-2 text-ink-muted">
        {hasWatchlist
          ? "Catchup will remember today's snapshot. When you return, it will show you what changed."
 : "Add stocks to your watchlist. When you return, Catchup will show you what changed."}
      </p>
      {!hasWatchlist && (
        <Link
          to="/watchlist"
          className="mt-5 inline-block rounded-md bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-ink-soft"
        >
          Add a stock
        </Link>
      )}
    </section>
  );
}
