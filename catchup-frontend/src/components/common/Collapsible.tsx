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
    <div className="rounded-lg border border-line bg-white">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold hover:bg-gray-50"
      >
        {title}
        <span aria-hidden>{open ? "−" : "+"}</span>
      </button>
      {open && <div className="border-t border-line px-4 py-3">{children}</div>}
    </div>
  );
}
