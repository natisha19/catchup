// Spinner.tsx
export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2.5 text-sm text-ink-muted"
    >
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-ink"
        aria-hidden
      />
      {label}…
    </div>
  );
}