// Spinner.tsx
export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 text-ink-muted text-sm">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-ink" aria-hidden />
      {label}…
    </div>
  );
}
