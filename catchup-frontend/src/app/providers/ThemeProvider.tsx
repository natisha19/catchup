import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "catchup-theme";
const LIGHT_META = "#F7F8FA";
const DARK_META = "#0F172A";

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  // Keep the browser chrome tint in sync with the palette we apply.
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? DARK_META : LIGHT_META);
}

/**
 * Centralized presentational theme. Legal values are exactly "light"|"dark".
 * Product logic never depends on this — it only ever toggles a class on <html>.
 * Preference: explicit user choice > system preference > light default.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() =>
    typeof document !== "undefined" && document.documentElement.classList.contains("dark")
      ? "dark"
      : "light",
  );

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Follow the OS while the user has not made an explicit choice.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      setTheme((current) => {
        try {
          if (localStorage.getItem(STORAGE_KEY)) return current;
        } catch {
          // Storage unavailable — fall through to the system preference.
        }
        return mq.matches ? "dark" : "light";
      });
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Storage unavailable — the toggle still applies for this session.
      }
      return next;
    });
  }, []);

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}

const ThemeContext = createContext<{ theme: Theme; toggle: () => void } | null>(null);

export function useTheme(): { theme: Theme; toggle: () => void } {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}