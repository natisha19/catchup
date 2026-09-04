const currencySymbols: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£" };

export function formatCurrency(value: number | null, currency = "INR"): string {
  if (value === null) return "—";
  const symbol = currencySymbols[currency] ?? currency;
  return `${symbol}${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function formatPercentage(value: number | null, digits = 2): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatSignedCurrency(value: number | null, currency = "INR"): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${formatCurrency(Math.abs(value), currency)}`;
}

export function formatVolume(value: number | null): string {
  if (value === null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

export function formatRatio(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)}×`;
}

export function formatSigma(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)}σ`;
}
