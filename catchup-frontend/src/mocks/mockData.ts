import type {
  ChangeSignal,
  Instrument,
  MarketSnapshot,
  WatchlistItem,
} from "../domain/types";

// Pure data. No formulas, no derived logic — mock values represent
// what a backend would have already computed.

export const instruments: Record<string, Instrument> = {
  tcs: { instrumentId: "tcs", symbol: "TCS", companyName: "Tata Consultancy Services", exchange: "NSE", currency: "INR", sector: "IT" },
  infy: { instrumentId: "infy", symbol: "INFY", companyName: "Infosys", exchange: "NSE", currency: "INR", sector: "IT" },
  reliance: { instrumentId: "reliance", symbol: "RELIANCE", companyName: "Reliance Industries", exchange: "NSE", currency: "INR", sector: "Energy" },
  hdfcbank: { instrumentId: "hdfcbank", symbol: "HDFCBANK", companyName: "HDFC Bank", exchange: "NSE", currency: "INR", sector: "Financials" },
  amd: { instrumentId: "amd", symbol: "AMD", companyName: "Advanced Micro Devices", exchange: "NASDAQ", currency: "USD", sector: "Semiconductors" },
};

export const watchlistItems: WatchlistItem[] = [
  { instrument: instruments.tcs, addedAt: "2025-01-10T09:00:00Z", baselineStatus: "READY" },
  { instrument: instruments.infy, addedAt: "2025-01-10T09:05:00Z", baselineStatus: "READY" },
  { instrument: instruments.reliance, addedAt: "2025-01-11T10:00:00Z", baselineStatus: "READY" },
  { instrument: instruments.hdfcbank, addedAt: "2025-01-12T11:00:00Z", baselineStatus: "READY" },
  { instrument: instruments.amd, addedAt: "2025-01-14T08:30:00Z", baselineStatus: "READY" },
];

export const snapshots: Record<string, MarketSnapshot> = {
  tcs: { instrumentId: "tcs", observedAt: "2025-01-15T15:30:00+05:30", receivedAt: "2025-01-15T15:30:05+05:30", price: 3945, open: 3830, high: 3958, low: 3822, close: null, volume: 8_240_000, source: "provider-a", dataStatus: "LIVE" },
  infy: { instrumentId: "infy", observedAt: "2025-01-15T15:30:00+05:30", receivedAt: "2025-01-15T15:30:04+05:30", price: 1642, open: 1629, high: 1648, low: 1624, close: null, volume: 12_100_000, source: "provider-a", dataStatus: "LIVE" },
  reliance: { instrumentId: "reliance", observedAt: "2025-01-15T15:29:58+05:30", receivedAt: "2025-01-15T15:30:06+05:30", price: 1425, open: 1372, high: 1431, low: 1370, close: null, volume: 15_600_000, source: "provider-a", dataStatus: "LIVE" },
  hdfcbank: { instrumentId: "hdfcbank", observedAt: "2025-01-15T14:10:00+05:30", receivedAt: "2025-01-15T14:10:03+05:30", price: 1687, open: 1690, high: 1702, low: 1680, close: null, volume: 4_100_000, source: "provider-b", dataStatus: "STALE" },
  amd: { instrumentId: "amd", observedAt: "2025-01-15T13:00:00+05:30", receivedAt: undefined, price: null, open: null, high: null, low: null, close: null, volume: null, source: "provider-b", dataStatus: "UNAVAILABLE" },
};

export const signals: ChangeSignal[] = [
  {
    id: "sig-tcs-earnings", instrumentId: "tcs", symbol: "TCS", companyName: "Tata Consultancy Services",
    previousPrice: 3820, currentPrice: 3945, returnPct: 3.27,
    baselineMean: 0.9, baselineStd: 0.6, zScore: 2.7,
    currentVolume: 8_240_000, baselineAverageVolume: 3_450_000, volumeRatio: 2.4,
    eventType: "CORPORATE_EVENT", reasonCodes: ["SIGNIFICANT_PRICE_MOVE", "UNUSUAL_VOLUME", "EARNINGS_EVENT"],
    eventDescription: "Quarterly earnings released",
    significance: "SIGNIFICANT", observedAt: "2025-01-15T15:30:00+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-reliance-move", instrumentId: "reliance", symbol: "RELIANCE", companyName: "Reliance Industries",
    previousPrice: 1370, currentPrice: 1425, returnPct: 4.01,
    baselineMean: 1.1, baselineStd: 0.55, zScore: 2.8,
    currentVolume: 15_600_000, baselineAverageVolume: 6_900_000, volumeRatio: 2.26,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE", "UNUSUAL_VOLUME"],
    eventDescription: "Unusual price movement",
    significance: "SIGNIFICANT", observedAt: "2025-01-15T15:29:58+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-infy-volume", instrumentId: "infy", symbol: "INFY", companyName: "Infosys",
    previousPrice: 1629, currentPrice: 1642, returnPct: 0.8,
    baselineMean: 0.7, baselineStd: 0.4, zScore: 0.25,
    currentVolume: 12_100_000, baselineAverageVolume: 6_400_000, volumeRatio: 1.9,
    eventType: "VOLUME_ANOMALY", reasonCodes: ["UNUSUAL_VOLUME"],
    eventDescription: "Trading volume increased",
    significance: "NOTABLE", observedAt: "2025-01-15T15:30:00+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-amd-critical", instrumentId: "amd", symbol: "AMD", companyName: "Advanced Micro Devices",
    previousPrice: 148.2, currentPrice: 171.6, returnPct: 15.79,
    baselineMean: 1.4, baselineStd: 1.1, zScore: 13.09,
    currentVolume: 96_500_000, baselineAverageVolume: 41_000_000, volumeRatio: 2.35,
    eventType: "CORPORATE_EVENT", reasonCodes: ["SIGNIFICANT_PRICE_MOVE", "EARNINGS_EVENT", "UNUSUAL_VOLUME"],
    eventDescription: "Earnings released with large gap-up",
    significance: "CRITICAL", observedAt: "2025-01-14T21:00:00+05:30", dataStatus: "UNAVAILABLE",
  },
];

export const lastCheckedAt = "2025-01-14T18:42:00+05:30";
export const marketSessionClosedAt = "2025-01-15T15:30:00+05:30";

export function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export function failure<T>(message: string, ms = 250): Promise<T> {
  return new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms));
}
