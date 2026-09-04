import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ChangeCard } from "../components/catchup/ChangeCard";
import type { ChangeSignal } from "../domain/types";

const signal: ChangeSignal = {
  id: "1", instrumentId: "tcs", symbol: "TCS", companyName: "Tata Consultancy Services",
  previousPrice: 3820, currentPrice: 3945, returnPct: 3.27,
  baselineMean: 0.9, baselineStd: 0.6, zScore: 2.7,
  currentVolume: 8_240_000, baselineAverageVolume: 3_450_000, volumeRatio: 2.4,
  eventType: "CORPORATE_EVENT", reasonCodes: ["EARNINGS_EVENT"],
  eventDescription: "Earnings released", significance: "SIGNIFICANT",
  observedAt: "2025-01-15T15:30:00+05:30", dataStatus: "LIVE",
};

const renderCard = (s: ChangeSignal) =>
  render(<MemoryRouter><ChangeCard signal={s} /></MemoryRouter>);

describe("ChangeCard", () => {
  it("renders meaningful data", () => {
    renderCard(signal);
    expect(screen.getByText("TCS")).toBeInTheDocument();
    expect(screen.getByText("Earnings released")).toBeInTheDocument();
    expect(screen.getByText("₹3,820 → ₹3,945")).toBeInTheDocument();
    expect(screen.getByText("+3.27%")).toBeInTheDocument();
    expect(screen.getByText(/2.4×/)).toBeInTheDocument();
  });

  it.each([
    ["CRITICAL", /Significance: critical/i],
    ["SIGNIFICANT", /Significance: significant/i],
    ["NOTABLE", /Significance: notable/i],
  ] as const)("renders %s state", (tier, expected) => {
    renderCard({ ...signal, significance: tier });
    expect(screen.getByLabelText(expected)).toBeInTheDocument();
  });

  it("marks stale data clearly", () => {
    renderCard({ ...signal, dataStatus: "STALE" });
    expect(screen.getByRole("status")).toHaveTextContent("Stale data");
  });
});
