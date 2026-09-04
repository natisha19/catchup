import { useState } from "react";
import type { UserRelevance } from "../../domain/types";

/** Displays backend-provided relevance only. No frontend inference. */
export function RelevancePrompt({ relevance }: { relevance: UserRelevance }) {
  const [dismissed, setDismissed] = useState<"keep" | "change" | null>(null);
  if (dismissed) return null;

  return (
    <div
      role="note"
      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-card px-4 py-3 shadow-card"
    >
      <p className="flex items-center gap-2.5 text-sm text-ink-soft">
        <span
          aria-hidden
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
            <path
              d="M12 8h.01M11 12h1v4h1"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        {relevance.summary}
      </p>
      <div className="flex gap-2">
        <button onClick={() => setDismissed("keep")} className="btn px-3 py-1 text-xs">
          Keep
        </button>
        <button onClick={() => setDismissed("change")} className="text-xs font-medium text-ink-muted hover:text-ink">
          Change
        </button>
      </div>
    </div>
  );
}