import type { WatchlistApi } from "../api/watchlistApi";
import type { Instrument, Watchlist } from "../domain/types";
import * as data from "./mockData";

export class MockWatchlistApi implements WatchlistApi {
  private items = [...data.watchlistItems];

  async getWatchlist(): Promise<Watchlist> {
    return data.delay({ items: this.items, updatedAt: new Date().toISOString() });
  }

  async addInstrument(instrumentId: string, symbol?: string): Promise<void> {
    const id = symbol ?? instrumentId;
    const instrument = data.instruments[id] ?? {
      instrumentId: id,
      symbol: id,
      companyName: id,
      exchange: "YAHOO",
      currency: "USD",
    };
    if (!this.items.some((i) => i.instrument.instrumentId === id)) {
      // New instruments have no baseline yet — backend would report this.
      this.items.push({
        instrument,
        addedAt: new Date().toISOString(),
        baselineStatus: "INSUFFICIENT",
      });
    }
    return data.delay(undefined);
  }

  async removeInstrument(instrumentId: string): Promise<void> {
    this.items = this.items.filter((i) => i.instrument.instrumentId !== instrumentId);
    return data.delay(undefined);
  }
}

export class MockInstrumentApi {
  private all = Object.values(data.instruments);

  async search(query: string): Promise<{ instrument: Instrument }[]> {
    const q = query.trim().toUpperCase();
    const results = this.all
      .filter(
        (i) => i.symbol.includes(q) || i.companyName.toUpperCase().includes(q),
      )
      .map((instrument) => ({ instrument }));
    return data.delay(results);
  }
}

export const mockWatchlistApi = new MockWatchlistApi();
export const mockInstrumentApi = new MockInstrumentApi();
