import { Link, NavLink, Outlet } from "react-router-dom";
import { useTheme } from "../../app/providers/ThemeProvider";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? "font-semibold text-ink"
    : "font-medium text-ink-muted transition-colors hover:text-ink";

export function AppShell() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
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
                  Explore
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
                  Catchup
                </span>
              )}
            </NavLink>
            <button
              type="button"
              onClick={toggle}
              aria-label={`Switch to ${dark ? "light" : "dark"} theme`}
              title={`Switch to ${dark ? "light" : "dark"} theme`}
              className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-card text-ink-soft transition-colors hover:text-ink"
            >
              {dark ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth="1.8" />
                  <path
                    d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path
                    d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </button>
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