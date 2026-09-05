import type {
  ChangeSignal,
  Explore,
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
  titan: { instrumentId: "titan", symbol: "TITAN", companyName: "Titan Company", exchange: "NSE", currency: "INR", sector: "Consumer" },
  hindunilvr: { instrumentId: "hindunilvr", symbol: "HINDUNILVR", companyName: "Hindustan Unilever", exchange: "NSE", currency: "INR", sector: "Consumer" },
  sunpharma: { instrumentId: "sunpharma", symbol: "SUNPHARMA", companyName: "Sun Pharmaceutical Industries", exchange: "NSE", currency: "INR", sector: "Healthcare" },
  maruti: { instrumentId: "maruti", symbol: "MARUTI", companyName: "Maruti Suzuki India", exchange: "NSE", currency: "INR", sector: "Automobiles" },
};

// New users start with an empty watchlist (spec §12). The seeded universe is
// the discovery catalog the Explore page reads from.
export const watchlistItems: WatchlistItem[] = [];

export const snapshots: Record<string, MarketSnapshot> = {
  tcs: { instrumentId: "tcs", observedAt: "2025-01-15T15:30:00+05:30", receivedAt: "2025-01-15T15:30:05+05:30", price: 3945, open: 3830, high: 3958, low: 3822, close: null, volume: 8_240_000, source: "provider-a", dataStatus: "LIVE" },
  infy: { instrumentId: "infy", observedAt: "2025-01-15T15:30:00+05:30", receivedAt: "2025-01-15T15:30:04+05:30", price: 1642, open: 1629, high: 1648, low: 1624, close: null, volume: 12_100_000, source: "provider-a", dataStatus: "LIVE" },
  reliance: { instrumentId: "reliance", observedAt: "2025-01-15T15:29:58+05:30", receivedAt: "2025-01-15T15:30:06+05:30", price: 1425, open: 1372, high: 1431, low: 1370, close: null, volume: 15_600_000, source: "provider-a", dataStatus: "LIVE" },
  hdfcbank: { instrumentId: "hdfcbank", observedAt: "2025-01-15T14:10:00+05:30", receivedAt: "2025-01-15T14:10:03+05:30", price: 1687, open: 1741, high: 1750, low: 1682, close: null, volume: 4_100_000, source: "provider-b", dataStatus: "STALE" },
  amd: { instrumentId: "amd", observedAt: "2025-01-15T13:00:00+05:30", receivedAt: undefined, price: null, open: null, high: null, low: null, close: null, volume: null, source: "provider-b", dataStatus: "UNAVAILABLE" },
  titan: { instrumentId: "titan", observedAt: "2025-01-15T15:29:56+05:30", receivedAt: "2025-01-15T15:30:00+05:30", price: 3422, open: 3358, high: 3440, low: 3350, close: null, volume: 2_150_000, source: "provider-a", dataStatus: "LIVE" },
  hindunilvr: { instrumentId: "hindunilvr", observedAt: "2025-01-15T15:29:57+05:30", receivedAt: "2025-01-15T15:30:01+05:30", price: 2448, open: 2510, high: 2522, low: 2440, close: null, volume: 3_900_000, source: "provider-a", dataStatus: "LIVE" },
  sunpharma: { instrumentId: "sunpharma", observedAt: "2025-01-15T15:29:59+05:30", receivedAt: "2025-01-15T15:30:03+05:30", price: 1905, open: 1795, high: 1912, low: 1789, close: null, volume: 6_800_000, source: "provider-a", dataStatus: "LIVE" },
  maruti: { instrumentId: "maruti", observedAt: "2025-01-15T15:29:55+05:30", receivedAt: "2025-01-15T15:29:59+05:30", price: 12840, open: 13300, high: 13340, low: 12820, close: null, volume: 1_400_000, source: "provider-a", dataStatus: "LIVE" },
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
  {
    id: "sig-sunpharma-rally", instrumentId: "sunpharma", symbol: "SUNPHARMA", companyName: "Sun Pharmaceutical Industries",
    previousPrice: 1795, currentPrice: 1905, returnPct: 6.13,
    baselineMean: 0.9, baselineStd: 0.7, zScore: 7.47,
    currentVolume: 6_800_000, baselineAverageVolume: 3_200_000, volumeRatio: 2.13,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE", "UNUSUAL_VOLUME"],
    eventDescription: "Unusual price movement",
    significance: "SIGNIFICANT", observedAt: "2025-01-15T15:29:59+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-titan-move", instrumentId: "titan", symbol: "TITAN", companyName: "Titan Company",
    previousPrice: 3350, currentPrice: 3422, returnPct: 2.15,
    baselineMean: 0.8, baselineStd: 0.5, zScore: 2.7,
    currentVolume: 2_150_000, baselineAverageVolume: 1_900_000, volumeRatio: 1.13,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE"],
    eventDescription: "Unusual price movement",
    significance: "NOTABLE", observedAt: "2025-01-15T15:29:56+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-maruti-drop", instrumentId: "maruti", symbol: "MARUTI", companyName: "Maruti Suzuki India",
    previousPrice: 13300, currentPrice: 12840, returnPct: -3.46,
    baselineMean: 1.2, baselineStd: 0.9, zScore: -5.18,
    currentVolume: 1_400_000, baselineAverageVolume: 1_100_000, volumeRatio: 1.27,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE"],
    eventDescription: "Unusual price movement",
    significance: "SIGNIFICANT", observedAt: "2025-01-15T15:29:55+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-hindunilvr-drop", instrumentId: "hindunilvr", symbol: "HINDUNILVR", companyName: "Hindustan Unilever",
    previousPrice: 2510, currentPrice: 2448, returnPct: -2.47,
    baselineMean: 1.1, baselineStd: 0.9, zScore: -3.97,
    currentVolume: 3_900_000, baselineAverageVolume: 1_850_000, volumeRatio: 2.11,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE", "UNUSUAL_VOLUME"],
    eventDescription: "Unusual price movement",
    significance: "SIGNIFICANT", observedAt: "2025-01-15T15:29:57+05:30", dataStatus: "LIVE",
  },
  {
    id: "sig-hdfcbank-drop", instrumentId: "hdfcbank", symbol: "HDFCBANK", companyName: "HDFC Bank",
    previousPrice: 1741, currentPrice: 1687, returnPct: -3.1,
    baselineMean: 0.7, baselineStd: 1.2, zScore: -3.17,
    currentVolume: 4_100_000, baselineAverageVolume: 4_500_000, volumeRatio: 0.91,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE"],
    eventDescription: "Unusual price movement",
    significance: "NOTABLE", observedAt: "2025-01-15T14:10:00+05:30", dataStatus: "STALE",
  },
];

export const lastCheckedAt = "2025-01-14T18:42:00+05:30";
export const marketSessionClosedAt = "2025-01-15T15:30:00+05:30";

// Mirrors the backend's composition-based summary (spec §16) — the mock holds
// the already-composed string, never a fabrication from the UI.
export const relevanceSummary =
  "IT is the most common sector in your watchlist (2 of 5 stocks).";

// Discovery feed for the Explore page: a fixed snapshot of what
// /instruments/explore returns. Rankings are pre-computed data here.
function exploreItem(id: keyof typeof instruments): {
  instrument: Instrument;
  snapshot: MarketSnapshot | null;
  signal: ChangeSignal | null;
} {
  return {
    instrument: instruments[id],
    snapshot: snapshots[id] ?? null,
    signal: signals.find((s) => s.instrumentId === id) ?? null,
  };
}

export const explore: Explore = {
  movers: [exploreItem("sunpharma"), exploreItem("reliance"), exploreItem("tcs"), exploreItem("titan"), exploreItem("infy")],
  dippers: [exploreItem("maruti"), exploreItem("hindunilvr"), exploreItem("hdfcbank")],
  unusual: [exploreItem("amd"), exploreItem("sunpharma"), exploreItem("maruti"), exploreItem("reliance")],
  sectors: ["Automobiles", "Consumer", "Energy", "Financials", "Healthcare", "IT", "Semiconductors"],
};

export function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export function failure<T>(message: string, ms = 250): Promise<T> {
  return new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms));
}
