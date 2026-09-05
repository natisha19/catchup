import type { CatchupApi } from "../api/catchupApi";
import type { ChangeDetail, CatchupFeed, MarketStatus } from "../domain/types";
import * as data from "./mockData";

export type MockScenario = "default" | "firstVisit" | "marketClosed" | "noChanges" | "apiDown";

let currentScenario: MockScenario = "default";

export function setMockScenario(s: MockScenario) {
  currentScenario = s;
}

const exchangeStatus: Record<string, MarketStatus> = {
  NSE: "CLOSED",
  NASDAQ: "CLOSED",
  NYSE: "CLOSED",
};

export class MockCatchupApi implements CatchupApi {
  async getFeed(): Promise<CatchupFeed> {
    if (currentScenario === "apiDown") {
      return data.failure("Provider unreachable");
    }
    // Default is the honest new-user story: an empty watchlist, nothing to
    // catch up on yet (spec §12).
    if (currentScenario === "default" || currentScenario === "firstVisit") {
      return data.delay({
        lastCheckedAt: null,
        marketStatus: "CLOSED",
        lastMarketSessionAt: null,
        changes: [],
        unchangedCount: 0,
        providerStatus: "AVAILABLE",
        userRelevance: null,
        acknowledgement: {},
      });
    }
    if (currentScenario === "marketClosed") {
      return data.delay({
        lastCheckedAt: data.lastCheckedAt,
        marketStatus: "CLOSED",
        lastMarketSessionAt: data.marketSessionClosedAt,
        changes: [data.signals[0], data.signals[1]],
        unchangedCount: 1,
        providerStatus: "AVAILABLE",
        userRelevance: {
          summary: data.relevanceSummary,
          topReasonCodes: [],
        },
        acknowledgement: { tcs: 101, infy: 102 },
      });
    }
    return data.delay({
      lastCheckedAt: data.lastCheckedAt,
      marketStatus: "OPEN",
      lastMarketSessionAt: null,
      changes: [],
      unchangedCount: 12,
      providerStatus: "AVAILABLE",
      userRelevance: null,
      acknowledgement: {},
    });
  }

  async getInstrumentChange(instrumentId: string): Promise<ChangeDetail> {
    if (currentScenario === "apiDown") return data.failure("Provider unavailable");
    // Mirrors the real endpoint: any known/cataloged instrument resolves to a
    // detail, even when no snapshot exists yet (freshly added stock).
    const instrument =
      data.instruments[instrumentId] ?? {
        instrumentId,
        symbol: instrumentId,
        companyName: instrumentId,
        exchange: "YAHOO",
        currency: "USD",
      };
    const snapshot = data.snapshots[instrumentId] ?? null;
    const latestSignal =
      data.signals.find((s) => s.instrumentId === instrumentId) ?? null;
    return data.delay({
      instrument,
      snapshot,
      previousSeenPrice:
        currentScenario === "firstVisit" ? null : (latestSignal?.previousPrice ?? null),
      latestSignal,
      otherSignals: [],
      marketStatus: exchangeStatus[instrument.exchange] ?? "UNKNOWN",
    });
  }

  async markSeen(): Promise<void> {
    return data.delay(undefined);
  }
}

export const mockCatchupApi = new MockCatchupApi();
