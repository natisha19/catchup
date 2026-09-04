/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#101418", soft: "#3d454d", muted: "#6b7480" },
        paper: "#fafbfc",
        line: "#e4e7eb",
        signal: {
          critical: "#b42318",
          significant: "#b54708",
          notable: "#175cd3",
          normal: "#475467",
        },
        up: "#027a48",
        down: "#b42318",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
