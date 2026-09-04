import type { ChangeSignal, MarketStatus, SignificanceTier } from "../../domain/types";
import { ChangeCard } from "./ChangeCard";

const tierOrder: Record<SignificanceTier, number> = {
  CRITICAL: 0, SIGNIFICANT: 1, NOTABLE: 2, NORMAL: 3,
};

/** Presentation-only ranking; CRITICAL events are never filtered out. */
export function ChangeFeed({
  changes,
  marketStatus,
}: {
  changes: ChangeSignal[];
  marketStatus?: MarketStatus;
}) {
  const ranked = [...changes].sort(
    (a, b) => tierOrder[a.significance] - tierOrder[b.significance],
  );
  return (
    <div className="space-y-4">
      {ranked.map((s) => (
        <div key={s.id} className="animate-fade-in">
          <ChangeCard signal={s} marketStatus={marketStatus} />
        </div>
      ))}
    </div>
  );
}