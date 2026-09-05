// src/tests/ExplorePage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExplorePage } from "../pages/ExplorePage";

vi.mock("../hooks/useApis", () => ({ useApis: vi.fn() }));

import { useApis } from "../hooks/useApis";

const makeItem = (id: string, symbol: string, sector: string, ret: number) => ({
  instrument: { instrumentId: id, symbol, companyName: `${symbol} Corp`, exchange: "NSE", currency: "INR", sector },
  snapshot: { instrumentId: id, observedAt: "2025-01-15T15:30:00+05:30", price: 100, open: 99, high: 105, low: 95, volume: 1_000, source: "provider-a", dataStatus: "LIVE" },
  signal: {
    id: `s-${id}`, instrumentId: id, symbol, companyName: `${symbol} Corp`,
    previousPrice: 95, currentPrice: 100, returnPct: ret, baselineMean: 1, baselineStd: 0.5,
    zScore: 2, currentVolume: 1_000, baselineAverageVolume: 500, volumeRatio: 2,
    eventType: "PRICE_ANOMALY", reasonCodes: ["SIGNIFICANT_PRICE_MOVE"],
    eventDescription: "Unusual price movement", significance: "SIGNIFICANT",
    observedAt: "2025-01-15T15:30:00+05:30", dataStatus: "LIVE",
  },
});

const populatedExplore = {
  movers: [makeItem("sunpharma", "SUNPHARMA", "Healthcare", 6.13)],
  dippers: [makeItem("maruti", "MARUTI", "Automobiles", -3.46)],
  unusual: [makeItem("amd", "AMD", "Semiconductors", 15.79)],
  sectors: ["Automobiles", "Healthcare", "Semiconductors"],
};

const mockExplore = { getExplore: vi.fn() };
const mockWatchlist = {
  getWatchlist: vi.fn().mockResolvedValue({ items: [], updatedAt: "2025-01-15T00:00:00Z" }),
  addInstrument: vi.fn().mockResolvedValue(undefined),
  removeInstrument: vi.fn().mockResolvedValue(undefined),
};
const mockInstrument = { search: vi.fn() };

function setup() {
  vi.mocked(useApis).mockReturnValue({
    explore: mockExplore,
    watchlist: mockWatchlist,
    instrument: mockInstrument,
  } as never);
}

const renderPage = () =>
  render(
    <MemoryRouter>
      <ExplorePage />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  mockExplore.getExplore.mockResolvedValue(populatedExplore);
  mockWatchlist.getWatchlist.mockResolvedValue({ items: [], updatedAt: "2025-01-15T00:00:00Z" });
});

describe("ExplorePage", () => {
  it("renders movers, dippers and unusual sections with sector chips", async () => {
    setup();
    renderPage();
    expect(await screen.findByText("SUNPHARMA")).toBeInTheDocument();
    expect(screen.getByText("MARUTI")).toBeInTheDocument();
    expect(screen.getByText("AMD")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Filter by sector" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Healthcare" })).toBeInTheDocument();
  });

  it("shows an honest awaiting-data state when there are no movers yet", async () => {
    setup();
    mockExplore.getExplore.mockResolvedValue({ movers: [], dippers: [], unusual: [], sectors: [] });
    renderPage();
    expect(await screen.findByText(/Awaiting first market data/)).toBeInTheDocument();
  });

  it("renders an API failure state with retry", async () => {
    setup();
    mockExplore.getExplore.mockRejectedValue(new Error("Provider down"));
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load market movers");
  });

  it("refetches the feed for a sector so the backend query is genuinely scoped", async () => {
    const user = userEvent.setup();
    setup();
    mockExplore.getExplore.mockImplementation(async (_limit?: number, sector?: string) => {
      if (!sector) return populatedExplore;
      const scoped = (rows: ReturnType<typeof makeItem>[]) =>
        rows.filter((i) => i.instrument.sector === sector);
      return {
        movers: scoped(populatedExplore.movers),
        dippers: scoped(populatedExplore.dippers),
        unusual: scoped(populatedExplore.unusual),
        sectors: populatedExplore.sectors,
      };
    });
    renderPage();
    await screen.findByText("SUNPHARMA");
    await user.click(screen.getByRole("button", { name: "Healthcare" }));
    await waitFor(() =>
      expect(mockExplore.getExplore).toHaveBeenCalledWith(undefined, "Healthcare"),
    );
    // The refetched feed now only contains Healthcare rows.
    expect(await screen.findByText("SUNPHARMA")).toBeInTheDocument();
    expect(screen.queryByText("MARUTI")).not.toBeInTheDocument();
  });

  it("shows an honest per-sector empty state when a sector has no valid data", async () => {
    const user = userEvent.setup();
    setup();
    mockExplore.getExplore.mockImplementation(async (_limit?: number, sector?: string) => {
      if (sector !== "Healthcare") return populatedExplore;
      return { movers: [], dippers: [], unusual: [], sectors: populatedExplore.sectors };
    });
    renderPage();
    await screen.findByText("SUNPHARMA");
    await user.click(screen.getByRole("button", { name: "Healthcare" }));
    expect(await screen.findByText(/No Healthcare stocks have valid market data/)).toBeInTheDocument();
    // The chips stay stable so the sector isn't mistaken for a gone feature.
    expect(screen.getByRole("button", { name: "Healthcare" })).toBeInTheDocument();
  });

  it("adds a searched instrument from the hero search", async () => {
    const user = userEvent.setup();
    setup();
    mockInstrument.search.mockResolvedValue([{ instrument: populatedExplore.movers[0].instrument }]);
    renderPage();
    await user.type(await screen.findByLabelText("Search all instruments"), "SUN");
    await user.click(await screen.findByRole("button", { name: /Add to watchlist/ }));
    await waitFor(() =>
      expect(mockWatchlist.addInstrument).toHaveBeenCalledWith("sunpharma", "SUNPHARMA"),
    );
  });

  it("filters already-watched instruments out of search results", async () => {
    const user = userEvent.setup();
    setup();
    mockWatchlist.getWatchlist.mockResolvedValue({
      items: [{ instrument: populatedExplore.movers[0].instrument, addedAt: "2025-01-10T09:00:00Z", baselineStatus: "READY" }],
      updatedAt: "2025-01-15T00:00:00Z",
    });
    mockInstrument.search.mockResolvedValue([{ instrument: populatedExplore.movers[0].instrument }]);
    renderPage();
    await user.type(await screen.findByLabelText("Search all instruments"), "SUN");
    // Watched matches are filtered out rather than offered for re-adding.
    expect(await screen.findByText(/is already in your watchlist/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add to watchlist/ })).not.toBeInTheDocument();
  });
});