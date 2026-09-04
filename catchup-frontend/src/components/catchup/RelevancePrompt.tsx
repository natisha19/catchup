import { useState } from "react";
import type { UserRelevance } from "../../domain/types";

/** Displays backend-provided relevance only. No frontend inference. */
export function RelevancePrompt({ relevance }: { relevance: UserRelevance }) {
  const [dismissed, setDismissed] = useState<"keep" | "change" | null>(null);
  if (dismissed) return null;

  return (
    <div role="note" className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 text-sm">
      <p className="text-ink-soft">{relevance.summary}</p>
      <div className="flex gap-2">
        <button
 onClick={() => setDismissed("keep")}
          className="rounded-md border border-line px-3 py-1 font-medium hover:bg-gray-50"
        >
          Keep
        </button>
        <button
          onClick={() => setDismissed("change")}
          className="rounded-md border border-line px-3 py-1 text-ink-muted hover:bg-gray-50"
        >
          Change
        </button>
      </div>
    </div>
  );
}
