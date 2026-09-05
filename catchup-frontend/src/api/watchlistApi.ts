import type { ChangeDetail, Instrument, Watchlist } from "../domain/types";

export interface WatchlistApi {
  getWatchlist(): Promise<Watchlist>;
  getMarketSnapshots(): Promise<ChangeDetail[]>;
  /**
   * Add an instrument to the watchlist.
   * `instrumentId` references an already-known instrument; `symbol` allows the
   * backend to resolve + persist a stock that is not yet in its catalog.
   */
  addInstrument(instrumentId: string, symbol?: string): Promise<void>;
  removeInstrument(instrumentId: string): Promise<void>;
}

export interface InstrumentSearchResult {
  instrument: Instrument;
}

export interface InstrumentApi {
  search(query: string): Promise<InstrumentSearchResult[]>;
}
