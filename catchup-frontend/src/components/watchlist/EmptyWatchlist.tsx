import { Link } from "react-router-dom";

export function EmptyWatchlist() {
  return (
    <section className="rounded-lg border border-line bg-white p-8 text-center">
      <h2 className="text-lg font-semibold">Your watchlist is empty.</h2>
      <p className="mt-2 text-sm text-ink-muted">
        Add stocks you want Catchup to remember.
      </p>
      <Link
        to="/watchlist?add=1"
        className="mt-5 inline-block rounded-md bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-ink-soft"
      >
        Add a stock
      </Link>
    </section>
  );
}
