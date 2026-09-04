// Collapsible.tsx
import { useState, type ReactNode } from "react";

export function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold text-ink transition-colors hover:bg-paper"
      >
        {title}
        <span
          aria-hidden
          className={`text-ink-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M6 9l6 6 6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>
      {open && <div className="border-t border-line px-4 py-3">{children}</div>}
    </div>
  );
}