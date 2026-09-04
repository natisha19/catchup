import type { WatchlistApi } from "../api/watchlistApi";
import type { Instrument, Watchlist } from "../domain/types";
import * as data from "./mockData";

export class MockWatchlistApi implements WatchlistApi {
  private items = [...data.watchlistItems];

  async getWatchlist(): Promise<Watchlist> {
    return data.delay({ items: this.items, updatedAt: new Date().toISOString() });
  }

  async addInstrument(instrumentId: string, symbol?: string): Promise<void> {
    // Mirrors the backend: a known instrumentId wins; a bare symbol is only
    // used to resolve + persist a stock the catalog does not know yet.
    const id = instrumentId || symbol || "";
    const known = data.instruments[id.toLowerCase()];
    const instrument = known ?? {
      instrumentId: id,
      symbol: id,
      companyName: id,
      exchange: "YAHOO",
      currency: "USD",
    };
    if (!this.items.some((i) => i.instrument.instrumentId === instrument.instrumentId)) {
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
