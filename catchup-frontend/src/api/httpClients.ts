/**
 * Real HTTP implementations of the API interfaces.
 *
 * Each method maps 1:1 onto a backend endpoint and relies on `httpJson` for the
 * transport (base URL, headers, error handling). Components never see these
 * classes directly — they are selected by `ApiProvider` based on config.
 */

import type { CatchupApi } from "./catchupApi";
import type { ExploreApi } from "./exploreApi";
import type { InstrumentApi, WatchlistApi } from "./watchlistApi";
import { httpJson } from "./clients";
import type { ChangeDetail, CatchupFeed, Explore, Watchlist } from "../domain/types";

const JSON_HEADERS = { "Content-Type": "application/json" };

export class HttpCatchupApi implements CatchupApi {
  async getFeed(): Promise<CatchupFeed> {
    return httpJson<CatchupFeed>("/catchup");
  }

  async getInstrumentChange(instrumentId: string): Promise<ChangeDetail> {
    return httpJson<ChangeDetail>(`/catchup/${encodeURIComponent(instrumentId)}`);
  }

  async markSeen(snapshotIds?: Record<string, number | null>, instrumentId?: string): Promise<void> {
    const body: { instrumentId?: string; snapshotIds?: Record<string, number | null> } = {};
    if (instrumentId) body.instrumentId = instrumentId;
    if (snapshotIds) body.snapshotIds = snapshotIds;
    await httpJson<void>("/catchup/mark-seen", {
      method: "POST",
      headers: JSON_HEADERS,
      body: Object.keys(body).length ? JSON.stringify(body) : undefined,
    });
  }
}

export class HttpWatchlistApi implements WatchlistApi {
  async getWatchlist(): Promise<Watchlist> {
    return httpJson<Watchlist>("/watchlists/me");
  }

  async getMarketSnapshots(): Promise<ChangeDetail[]> {
    return httpJson<ChangeDetail[]>("/watchlists/me/snapshots");
  }

  async addInstrument(instrumentId: string, symbol?: string): Promise<void> {
    const body: { instrumentId?: string; symbol?: string } = {};
    if (instrumentId) body.instrumentId = instrumentId;
    if (symbol) body.symbol = symbol;
    await httpJson<void>("/watchlists/me/items", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    });
  }

  async removeInstrument(instrumentId: string): Promise<void> {
    await httpJson<void>(`/watchlists/me/items/${encodeURIComponent(instrumentId)}`, {
      method: "DELETE",
    });
  }
}

export class HttpInstrumentApi implements InstrumentApi {
  async search(query: string): Promise<{ instrument: import("../domain/types").Instrument }[]> {
    const q = encodeURIComponent(query);
    return httpJson<{ instrument: import("../domain/types").Instrument }[]>(
      `/instruments/search?q=${q}`,
    );
  }
}

export class HttpExploreApi implements ExploreApi {
  async getExplore(limit?: number, sector?: string): Promise<Explore> {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (sector) params.set("sector", sector);
    const qs = params.toString();
    return httpJson<Explore>(`/instruments/explore${qs ? `?${qs}` : ""}`);
  }
}
