import type { ChangeDetail, CatchupFeed } from "../domain/types";

export interface CatchupApi {
  getFeed(): Promise<CatchupFeed>;
  getInstrumentChange(instrumentId: string): Promise<ChangeDetail>;
  markSeen(snapshotIds?: Record<string, number | null>, instrumentId?: string): Promise<void>;
}
