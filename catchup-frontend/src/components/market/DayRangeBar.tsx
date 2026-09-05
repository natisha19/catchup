/**
 * Tiny real-data visualization: where the current price sits within the day's
 * range (snapshot high/low). No chart library, no fabricated series — renders
 * only what the backend snapshot already provides.
 */
export function DayRangeBar({
  low,
  high,
  current,
  open,
}: {
  low: number | null;
  high: number | null;
  current: number | null;
  open?: number | null;
}) {
  if (low === null || high === null || current === null || high <= low) return null;
  const pos = Math.min(100, Math.max(0, ((current - low) / (high - low)) * 100));
  const ups = open !== null && open !== undefined ? current >= open : null;
  const tone = ups === null ? "bg-ink-soft" : ups ? "bg-up" : "bg-down";
  return (
    <div
      role="img"
      aria-label={`Day range ${low} to ${high}, current ${current}`}
      className="relative h-1.5 w-full rounded-full bg-paper ring-1 ring-inset ring-line"
    >
      <span
        aria-hidden
        className={`absolute top-1/2 h-3 w-1 -translate-y-1/2 rounded-full ${tone}`}
        style={{ left: `${pos}%` }}
      />
    </div>
  );
}