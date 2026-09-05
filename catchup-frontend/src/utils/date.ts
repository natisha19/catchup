export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";

  return new Date(iso).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatTimeOnly(iso: string | null | undefined): string {
  if (!iso) return "—";

  return new Date(iso).toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatRelativeTime(
  iso: string | null | undefined,
  now = new Date()
): string {
  if (!iso) return "—";

  const diffMs = now.getTime() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60_000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;

  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;

  const days = Math.round(hours / 24);
  if (days === 1) return "yesterday";

  return `${days} days ago`;
}

export function formatLastChecked(
  iso: string | null | undefined
): string {
  if (!iso) return "—";

  const d = new Date(iso);
  const now = new Date();

  const dateFormatter = new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });

  const timeFormatter = new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "numeric",
    minute: "2-digit",
  });

  const date = dateFormatter.format(d);
  const today = dateFormatter.format(now);

  const yesterdayDate = new Date(now.getTime() - 86_400_000);
  const yesterday = dateFormatter.format(yesterdayDate);

  const time = timeFormatter.format(d);

  if (date === today) return `Today at ${time}`;
  if (date === yesterday) return `Yesterday at ${time}`;

  return `${d.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
  })} at ${time}`;
}