import type { CatchupApi } from "../api/catchupApi";
import type { ChangeDetail, CatchupFeed } from "../domain/types";
import * as data from "./mockData";

export type MockScenario = "default" | "firstVisit" | "marketClosed" | "noChanges" | "apiDown";

let currentScenario: MockScenario = "default";

export function setMockScenario(s: MockScenario) {
  currentScenario = s;
}

export class MockCatchupApi implements CatchupApi {
  async getFeed(): Promise<CatchupFeed> {
    if (currentScenario === "apiDown") {
      return data.failure("Provider unreachable");
    }
    if (currentScenario === "firstVisit") {
      return data.delay({
        lastCheckedAt: null,
        marketStatus: "OPEN",
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
          summary: "You seem to pay more attention to earnings and company events.",
          topReasonCodes: ["EARNINGS_EVENT", "SIGNIFICANT_PRICE_MOVE"],
        },
        acknowledgement: { tcs: 101, infy: 102 },
      });
    }
    if (currentScenario === "noChanges") {
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
    return data.delay({
      lastCheckedAt: data.lastCheckedAt,
      marketStatus: "OPEN",
      lastMarketSessionAt: null,
      changes: data.signals,
      unchangedCount: 1,
      providerStatus: "AVAILABLE",
      userRelevance: {
        summary: "You seem to pay more attention to earnings and company events.",
        topReasonCodes: ["EARNINGS_EVENT", "SIGNIFICANT_PRICE_MOVE"],
      },
      acknowledgement: { tcs: 101, infy: 102 },
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
        currentScenario === "firstVisit" ? null : (latestSignal?.previousPrice ?? instrumentId === "hdfcbank" ? 1698 : null),
      latestSignal,
      otherSignals: [],
    });
  }

  async markSeen(): Promise<void> {
    return data.delay(undefined);
  }
}

export const mockCatchupApi = new MockCatchupApi();
