// ErrorState.tsx
export function ErrorState({ title, message, onRetry }: {
  title: string; message?: string; onRetry?: () => void;
}) {
  return (
    <div role="alert" className="rounded-lg border border-line bg-white p-6 text-center">
      <p className="font-medium">{title}</p>
      {message && <p className="mt-1 text-sm text-ink-muted">{message}</p>}
      {onRetry && (
        <button onClick={onRetry} className="mt-4 rounded-md border border-line bg-white px-4 py-1.5 text-sm font-medium hover:bg-gray-50">
          Try again
        </button>
      )}
    </div>
  );
}
