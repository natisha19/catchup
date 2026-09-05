// src/tests/WatchlistPage.test.tsx (final version)
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WatchlistPage } from "../pages/WatchlistPage";

vi.mock("../hooks/useApis", () => ({ useApis: vi.fn() }));

import { useApis } from "../hooks/useApis";

const mockCommissionedFeed = {
  lastCheckedAt: null,
  marketStatus: "CLOSED" as const,
  changes: [],
  unchangedCount: 0,
  providerStatus: "AVAILABLE" as const,
  userRelevance: null,
  acknowledgement: {},
};

const mockCatchup = {
  getFeed: vi.fn().mockResolvedValue(mockCommissionedFeed),
  getInstrumentChange: vi.fn(),
  markSeen: vi.fn().mockResolvedValue(undefined),
};

const mockWatchlist = {
  getWatchlist: vi.fn(),
  getMarketSnapshots: vi.fn().mockResolvedValue([]),
  addInstrument: vi.fn().mockResolvedValue(undefined),
  removeInstrument: vi.fn().mockResolvedValue(undefined),
};

const mockInstrument = {
  search: vi.fn().mockResolvedValue([
    {
      instrument: {
        instrumentId: "tcs", symbol: "TCS",
        companyName: "Tata Consultancy Services", exchange: "NSE", currency: "INR",
      },
    },
  ]),
};

function setup() {
  vi.mocked(useApis).mockReturnValue({
    catchup: mockCatchup,
    watchlist: mockWatchlist,
    instrument: mockInstrument,
  } as never);
}

const renderPage = () =>
  render(
    <MemoryRouter>
      <WatchlistPage />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  mockWatchlist.getWatchlist.mockResolvedValue({ items: [], updatedAt: "2025-01-15T00:00:00Z" });
  mockCatchup.getFeed.mockResolvedValue(mockCommissionedFeed);
});

describe("WatchlistPage", () => {
  it("renders empty state when watchlist is empty", async () => {
    setup();
    renderPage();
    expect(await screen.findByText("Your watchlist is empty.")).toBeInTheDocument();
    expect(screen.getByText("Add stocks you want Catchup to remember.")).toBeInTheDocument();
  });

  it("shows a compact welcome box with exactly one Add-a-stock action on first visit", async () => {
    setup();
    renderPage();
    expect(await screen.findByText("Welcome to Catchup.")).toBeInTheDocument();
    // The page header owns the single clear primary CTA; no duplicate buttons.
    expect(screen.getByRole("button", { name: "Add a stock" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Add a stock" })).toHaveLength(1);
  });

  it("renders an API failure state", async () => {
    setup();
    mockWatchlist.getWatchlist.mockRejectedValue(new Error("Network down"));
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load your watchlist");});

  it("adding an instrument calls watchlistApi.addInstrument with id and symbol", async () => {
    setup();
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Your watchlist is empty.");
    await user.click(screen.getByRole("button", { name: "Add a stock" }));
    await user.type(await screen.findByPlaceholderText(/Search by symbol/), "TCS");
    await user.click(await screen.findByRole("button", { name: /Add to watchlist/ }));
    await waitFor(() =>
      expect(mockWatchlist.addInstrument).toHaveBeenCalledWith("tcs", "TCS"),
    );
  });

  it("surfaces an add failure instead of silently failing, and Try again retries", async () => {
    setup();
    mockWatchlist.addInstrument
      .mockRejectedValueOnce(new Error("Instrument already in watchlist: tcs"))
      .mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Your watchlist is empty.");
    await user.click(screen.getByRole("button", { name: "Add a stock" }));
    await user.type(await screen.findByPlaceholderText(/Search by symbol/), "TCS");
    await user.click(await screen.findByRole("button", { name: /Add to watchlist/ }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Unable to add");
    expect(alert).toHaveTextContent("TCS");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() =>
      expect(mockWatchlist.addInstrument).toHaveBeenCalledTimes(2),
    );
  });

  it("falls back to add-by-symbol when the catalog has no match", async () => {
    setup();
    mockInstrument.search.mockResolvedValue([]);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Your watchlist is empty.");
    await user.click(screen.getByRole("button", { name: "Add a stock" }));
    await user.type(await screen.findByPlaceholderText(/Search by symbol/), "TCS.NS");
    const fallback = await screen.findByRole("button", { name: /Add .*TCS\.NS.* by symbol/ });
    await user.click(fallback);
    await waitFor(() =>
      expect(mockWatchlist.addInstrument).toHaveBeenCalledWith("", "TCS.NS"),
    );
  });

  it("removing an item calls watchlistApi.removeInstrument", async () => {
    setup();
    mockWatchlist.getWatchlist.mockResolvedValue({
      items: [
        {
          instrument: {
            instrumentId: "tcs", symbol: "TCS",
            companyName: "Tata Consultancy Services", exchange: "NSE", currency: "INR",
          },
          addedAt: "2025-01-10T09:00:00Z",
          baselineStatus: "READY",
        },
      ],
      updatedAt: "2025-01-15T00:00:00Z",
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("link", { name: "TCS" });
    await user.click(screen.getByRole("button", { name: /Remove TCS/ }));
    await waitFor(() =>
      expect(mockWatchlist.removeInstrument).toHaveBeenCalledWith("tcs"),
    );
  });
});
