// ---------------------------------------------------------------------------
// Catchup domain contract.
// The frontend knows ONLY this contract. Backend implementation details
// (database, providers, anomaly math) are intentionally absent here.
// ---------------------------------------------------------------------------

export type SignificanceTier = "CRITICAL" | "SIGNIFICANT" | "NOTABLE" | "NORMAL";

export type DataStatus = "LIVE" | "DELAYED" | "STALE" | "UNAVAILABLE";

export type MarketStatus = "OPEN" | "CLOSED" | "UNKNOWN";

export type ProviderStatus = "AVAILABLE" | "DEGRADED" | "UNAVAILABLE";

export type ChangeEventType =
  | "PRICE_ANOMALY"
  | "VOLUME_ANOMALY"
  | "CORPORATE_EVENT"
  | "MARKET_CONTEXT"
  | "DATA_QUALITY";

export type UserRelevance = {
  summary: string; // e.g. "You seem to pay more attention to earnings and company events."
  topReasonCodes: string[];
};

export interface Instrument {
  instrumentId: string;
  symbol: string;
  companyName: string;
  exchange: string;
  currency: string;
  sector?: string;
}

export interface WatchlistItem {
  instrument: Instrument;
  addedAt: string;
  /** Null until the backend has enough history; drives "Baseline being established." */
  baselineStatus: "READY" | "INSUFFICIENT";
}

export interface Watchlist {
  items: WatchlistItem[];
  updatedAt: string;
}

export interface MarketSnapshot {
  instrumentId: string;
  observedAt: string;
  receivedAt?: string;
  price: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close?: number | null;
  volume?: number | null;
  source: string;
  dataStatus: DataStatus;
}

export interface ChangeSignal {
  id: string;
  instrumentId: string;
  symbol: string;
  companyName: string;
  previousPrice: number | null;
  currentPrice: number | null;
  returnPct: number | null;
  baselineMean: number | null;
  baselineStd: number | null;
  zScore: number | null;
  currentVolume: number | null;
  baselineAverageVolume: number | null;
  volumeRatio: number | null;
  eventType: ChangeEventType;
  reasonCodes: string[];
  eventDescription: string;
  significance: SignificanceTier;
  observedAt: string;
  dataStatus: DataStatus;
}

export interface ChangeDetail {
  instrument: Instrument;
  snapshot: MarketSnapshot | null; // null => unavailable
  previousSeenPrice: number | null; // null => first visit / no baseline
  latestSignal: ChangeSignal | null;
  otherSignals: ChangeSignal[];
  /** When the user last saw this instrument (ISO string), from the backend. */
  lastCheckedNote?: string | null;
}

export interface CatchupFeed {
  lastCheckedAt: string | null;
  marketStatus: MarketStatus;
  lastMarketSessionAt?: string | null;
  changes: ChangeSignal[];
  unchangedCount: number;
  providerStatus?: ProviderStatus;
  userRelevance?: UserRelevance | null;
  /** Exact snapshots delivered in this feed; used for race-safe acknowledgement. */
  acknowledgement: Record<string, number | null>;
}
