/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Every color is a CSS variable token (see src/app/providers/theme.css).
        // Light and dark values live there; Tailwind only wires class -> token.
        // Theme is a presentational concern — no component hardcodes colors or
        // sprinkles `dark:` variants, so dark mode cannot diverge page logic.
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        "ink-soft": "rgb(var(--color-ink-soft) / <alpha-value>)",
        "ink-muted": "rgb(var(--color-ink-muted) / <alpha-value>)",
        paper: "rgb(var(--color-paper) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        card: "rgb(var(--color-card) / <alpha-value>)",
        // Contrast text placed on `ink` (inverted in dark mode).
        onink: "rgb(var(--color-onink) / <alpha-value>)",
        accent: {
          DEFAULT: "rgb(var(--color-accent) / <alpha-value>)",
          soft: "rgb(var(--color-accent-soft) / <alpha-value>)",
          line: "rgb(var(--color-accent-line) / <alpha-value>)",
        },
        signal: {
          critical: "rgb(var(--color-signal-critical) / <alpha-value>)",
          significant: "rgb(var(--color-signal-significant) / <alpha-value>)",
          notable: "rgb(var(--color-signal-notable) / <alpha-value>)",
          normal: "rgb(var(--color-signal-normal) / <alpha-value>)",
        },
        up: "rgb(var(--color-up) / <alpha-value>)",
        upsoft: "rgb(var(--color-up-soft) / <alpha-value>)",
        upline: "rgb(var(--color-up-line) / <alpha-value>)",
        down: "rgb(var(--color-down) / <alpha-value>)",
        downsoft: "rgb(var(--color-down-soft) / <alpha-value>)",
        downline: "rgb(var(--color-down-line) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      maxWidth: {
        app: "1100px",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(16 24 40 / 0.04)",
        raised: "0 8px 24px -8px rgb(16 24 40 / 0.16)",
      },
    },
  },
  plugins: [],
};