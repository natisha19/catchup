import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { RawDataPanel } from "../components/catchup/RawDataPanel";
import type { ChangeDetail } from "../domain/types";
import { instruments, snapshots, signals } from "../mocks/mockData";

const detail: ChangeDetail = {
  instrument: instruments.tcs,
  snapshot: snapshots.tcs,
  previousSeenPrice: 3820,
  latestSignal: signals[0],
  otherSignals: [],
};

describe("RawDataPanel", () => {
  it("renders backend-provided evidence when expanded", async () => {
    const user = userEvent.setup();
    render(<RawDataPanel detail={detail} />);
    const toggle = screen.getByRole("button", { name: "Raw data" });
    expect(screen.queryByText("Z-score")).not.toBeInTheDocument();
    await user.click(toggle);
    expect(screen.getByText("Z-score")).toBeInTheDocument();
    expect(screen.getByText("Baseline std")).toBeInTheDocument();
    expect(screen.getByText("provider-a")).toBeInTheDocument();
    expect(screen.getByText("CORPORATE_EVENT")).toBeInTheDocument();
  });
});
