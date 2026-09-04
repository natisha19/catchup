// ErrorState.tsx
export function ErrorState({ title, message, onRetry }: {
  title: string; message?: string; onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="card flex flex-col items-center px-6 py-12 text-center"
    >
      <span
        aria-hidden
        className="flex h-11 w-11 items-center justify-center rounded-full bg-downsoft text-down"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 8v5m0 3v.01M10.3 4.2L3.4 16.2A1.8 1.8 0 004.9 19h14.2a1.8 1.8 0 001.5-2.8L13.7 4.2A1.8 1.8 0 0010.3 4.2z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <p className="mt-4 font-medium text-ink">{title}</p>
      {message && <p className="mt-1 max-w-sm text-sm text-ink-muted">{message}</p>}
      {onRetry && (
        <button onClick={onRetry} className="btn mt-5">
          Try again
        </button>
      )}
    </div>
  );
}