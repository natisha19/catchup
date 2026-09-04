import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { MarketSnapshots } from "../components/catchup/MarketSnapshots";
import type { ChangeDetail, WatchlistItem } from "../domain/types";

vi.mock("../hooks/useApis", () => ({ useApis: vi.fn() }));

import { useApis } from "../hooks/useApis";

const tcs: WatchlistItem = {
  instrument: {
    instrumentId: "tcs", symbol: "TCS", companyName: "Tata Consultancy Services", exchange: "NSE", currency: "INR",
  },
  addedAt: "2025-01-10T09:00:00Z",
  baselineStatus: "READY",
};

// A stock added this session: the backend returns a detail with no snapshot
// (no worker tick yet), so the feed must say so instead of hiding it.
const fresh: WatchlistItem = {
  instrument: {
    instrumentId: "wipro", symbol: "WIPRO", companyName: "Wipro", exchange: "NSE", currency: "INR",
  },
  addedAt: "2025-01-16T09:00:00Z",
  baselineStatus: "INSUFFICIENT",
};

const tcsDetail: ChangeDetail = {
  instrument: tcs.instrument,
  snapshot: {
    instrumentId: "tcs", observedAt: "2025-01-15T15:30:00+05:30", receivedAt: "2025-01-15T15:30:05+05:30",
    price: 3945, volume: 8_240_000, source: "provider-a", dataStatus: "LIVE",
  },
  previousSeenPrice: 3820,
  latestSignal: {
    id: "s", instrumentId: "tcs", symbol: "TCS", companyName: "Tata Consultancy Services",
    previousPrice: 3820, currentPrice: 3945, returnPct: 3.27,
    baselineMean: 0.9, baselineStd: 0.6, zScore: 2.7,
    currentVolume: 8_240_000, baselineAverageVolume: 3_450_000, volumeRatio: 2.4,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE"],
    eventDescription: "Unusual price movement", significance: "SIGNIFICANT",
    observedAt: "2025-01-15T15:30:00+05:30", dataStatus: "LIVE",
  },
  otherSignals: [],
};

const noDataDetail: ChangeDetail = {
  instrument: fresh.instrument,
  snapshot: null,
  previousSeenPrice: null,
  latestSignal: null,
  otherSignals: [],
};

function setup() {
  vi.mocked(useApis).mockReturnValue({
    catchup: {
      getInstrumentChange: vi.fn(async (id: string) =>
        id === "tcs" ? tcsDetail : noDataDetail,
      ),
    },
  } as never);
}

describe("MarketSnapshots", () => {
  it("shows real prices for watched stocks and an honest no-data state for fresh ones", async () => {
    setup();
    render(
      <MemoryRouter>
        <MarketSnapshots items={[tcs, fresh]} marketStatus="OPEN" />
      </MemoryRouter>,
    );
    expect(await screen.findByText("₹3,945")).toBeInTheDocument();
    expect(screen.getAllByText(/\+3\.27%/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Awaiting first market data/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh now" })).toBeInTheDocument();
  });

  it("dedupes repeated watchlist rows for the same instrument", async () => {
    setup();
    render(
      <MemoryRouter>
        <MarketSnapshots items={[tcs, fresh, tcs]} />
      </MemoryRouter>,
    );
    expect(await screen.findByText("₹3,945")).toBeInTheDocument();
    const tcsCards = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("href") === "/stock/tcs");
    expect(tcsCards).toHaveLength(2); // one grid card + one leader row, no duplicate card
  });

  it("derives leaderboards only from real returns — no data, no section", async () => {
    setup();
    render(
      <MemoryRouter>
        <MarketSnapshots items={[tcs, fresh]} />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Top performers")).toBeInTheDocument();
    const tcsLinks = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("href") === "/stock/tcs");
    expect(tcsLinks.length).toBeGreaterThanOrEqual(2); // grid cell + leader row
    expect(screen.queryByText("Biggest dips")).not.toBeInTheDocument();
  });
});