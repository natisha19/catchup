/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#111827", soft: "#3F4A5C", muted: "#667085" },
        paper: "#F7F8FA",
        line: "#E5E7EB",
        card: "#FFFFFF",
        // CATCHUP accent — used sparingly, never as the dominant color.
        accent: { DEFAULT: "#F59E0B", soft: "#FFF8E6", line: "#FDE68A" },
        signal: {
          critical: "#DC2626",
          significant: "#B45309",
          notable: "#175CD3",
          normal: "#475467",
        },
        up: "#16A34A",
        upsoft: "#F0FDF4",
        upline: "#BBF7D0",
        down: "#DC2626",
        downsoft: "#FEF2F2",
        downline: "#FECACA",
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