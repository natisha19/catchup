export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
  });
}

export function formatTimeOnly(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "numeric", minute: "2-digit",
  });
}

export function formatRelativeTime(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return "—";
  const diffMs = now.getTime() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `minsminute{mins} minuteminsminute{mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `hourshour{hours} hourhourshour{hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

export function formatLastChecked(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const isYesterday =
    new Date(now.getTime() - 86_400_000).toDateString() === d.toDateString();
  const time = d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (isToday) return `Today at ${time}`;
  if (isYesterday) return `Yesterday at ${time}`;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" }) + ` at ${time}`;
}
