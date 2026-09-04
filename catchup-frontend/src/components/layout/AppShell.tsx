import { Link, NavLink, Outlet } from "react-router-dom";

export function AppShell() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">CATCHUP</Link>
          <nav aria-label="Main" className="flex gap-4 text-sm">
            <NavLink to="/" end className={({ isActive }) => isActive ? "font-semibold text-ink" : "text-ink-muted hover:text-ink"}>Feed</NavLink>
            <NavLink to="/watchlist" className={({ isActive }) => isActive ? "font-semibold text-ink" : "text-ink-muted hover:text-ink"}>Watchlist</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-3xl px-4 pb-8 text-xs text-ink-muted">
        Catchup remembers what the market looked like when you last checked.
      </footer>
    </div>
  );
}