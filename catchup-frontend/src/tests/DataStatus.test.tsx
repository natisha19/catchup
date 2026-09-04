import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataStatusBadge } from "../components/common/DataStatusBadge";
import { SnapshotHeader } from "../components/market/SnapshotHeader";
import type { ChangeDetail, DataStatus } from "../domain/types";

describe("DataStatusBadge", () => {
  it.each([
    ["LIVE", "Live"],
    ["DELAYED", "Delayed"],
    ["STALE", "Stale data"],
    ["UNAVAILABLE", "Unavailable"],
  ] as const)("renders %s clearly", (status: DataStatus, expected: string) => {
    render(<DataStatusBadge status={status} />);
    expect(screen.getByRole("status")).toHaveTextContent(expected);
  });

  it("presents stale data from the last completed session as Latest session data when the market is closed", () => {
    render(<DataStatusBadge status="STALE" marketStatus="CLOSED" />);
    expect(screen.getByRole("status")).toHaveTextContent("Latest session data");
  });

  it("keeps Stale data when the market is open", () => {
    render(<DataStatusBadge status="STALE" marketStatus="OPEN" />);
    expect(screen.getByRole("status")).toHaveTextContent("Stale data");
  });
});

describe("Stale / unavailable data display", () => {
  const baseDetail = (snapshot: ChangeDetail["snapshot"]): ChangeDetail => ({
    instrument: {
      instrumentId: "hdfcbank", symbol: "HDFCBANK", companyName: "HDFC Bank", exchange: "NSE", currency: "INR",
    },
    snapshot,
    previousSeenPrice: 1698,
    latestSignal: null,
    otherSignals: [],
  });

  it("stale snapshot shows last-updated time and never implies freshness", () => {
    render(
      <SnapshotHeader
        detail={baseDetail({
          instrumentId: "hdfcbank",
          observedAt: "2025-01-15T14:10:00+05:30",
          receivedAt: "2025-01-15T14:10:03+05:30",
          price: 1687,
          volume: 4_100_000,
          source: "provider-b",
          dataStatus: "STALE",
        })}
        currency="INR"
      />,
    );
    expect(screen.getByText("Stale data")).toBeInTheDocument();
    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
  });

  it("labels the latest session data as such when the market is closed", () => {
    render(
      <SnapshotHeader
        detail={baseDetail({
          instrumentId: "hdfcbank",
          observedAt: "2025-01-09T15:28:00+05:30",
          receivedAt: "2025-01-09T15:28:01+05:30",
          price: 1687,
          volume: 4_100_000,
          source: "provider-b",
          dataStatus: "STALE",
        })}
        currency="INR"
        marketStatus="CLOSED"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Latest session data");
    expect(screen.getByText(/Observed/)).toBeInTheDocument();
    expect(screen.queryByText("Stale data")).not.toBeInTheDocument();
  });

  it("unavailable snapshot shows fallback message without inventing values", () => {
    render(
      <SnapshotHeader
        detail={baseDetail({
          instrumentId: "hdfcbank",
          observedAt: "2025-01-15T10:32:00+05:30",
          price: null,
          source: "provider-b",
          dataStatus: "UNAVAILABLE",
        })}
        currency="INR"
      />,
    );
    expect(
      screen.getByText(/Market data temporarily unavailable/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Showing last known data/)).toBeInTheDocument();
    expect(screen.queryByText("₹")).not.toBeInTheDocument();
  });
});
