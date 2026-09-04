import { Link, NavLink, Outlet } from "react-router-dom";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? "font-semibold text-ink"
    : "font-medium text-ink-muted transition-colors hover:text-ink";

export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="sticky top-0 z-40 border-b border-line bg-card/90 backdrop-blur">
        <div className="mx-auto flex max-w-app items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/" className="group flex items-baseline gap-1.5">
            <span className="text-[17px] font-bold tracking-tight text-ink">CATCHUP</span>
            <span aria-hidden className="text-[9px] font-semibold tracking-[0.18em] text-accent">
              ●
            </span>
          </Link>
          <nav aria-label="Main" className="flex items-center gap-1 text-sm">
            <NavLink to="/" end className={navLinkClass}>
              {({ isActive }) => (
                <span
                  className={`inline-flex rounded-lg px-3 py-1.5 transition-colors ${
                    isActive ? "bg-paper text-ink" : ""
                  }`}
                >
                  Feed
                </span>
              )}
            </NavLink>
            <NavLink to="/watchlist" className={navLinkClass}>
              {({ isActive }) => (
                <span
                  className={`inline-flex rounded-lg px-3 py-1.5 transition-colors ${
                    isActive ? "bg-paper text-ink" : ""
                  }`}
                >
                  Watchlist
                </span>
              )}
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-app flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>

      <footer className="mx-auto w-full max-w-app px-4 pb-8 text-xs text-ink-muted sm:px-6">
        <p>
          CATCHUP — remembers what the market looked like when you last checked.
        </p>
      </footer>
    </div>
  );
}