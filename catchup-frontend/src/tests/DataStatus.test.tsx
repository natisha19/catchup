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
