import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { CatchupApi } from "../../api/catchupApi";
import type { InstrumentApi, WatchlistApi } from "../../api/watchlistApi";
import { apiConfig } from "../../api/clients";
import {
  HttpCatchupApi,
  HttpInstrumentApi,
  HttpWatchlistApi,
} from "../../api/httpClients";
import { mockCatchupApi } from "../../mocks/mockCatchupApi";
import { mockWatchlistApi, mockInstrumentApi } from "../../mocks/mockWatchlistApi";

export interface ApiContainer {
  catchup: CatchupApi;
  watchlist: WatchlistApi;
  instrument: InstrumentApi;
}

// Select implementation based on configuration only. Components never do.
function buildContainer(): ApiContainer {
  if (apiConfig.mode === "http" && apiConfig.baseUrl) {
    return {
      catchup: new HttpCatchupApi(),
      watchlist: new HttpWatchlistApi(),
      instrument: new HttpInstrumentApi(),
    };
  }
  return {
    catchup: mockCatchupApi,
    watchlist: mockWatchlistApi,
    instrument: mockInstrumentApi,
  };
}

const ApiContext = createContext<ApiContainer | null>(null);

export function ApiProvider({ children }: { children: ReactNode }) {
  const container = useMemo(buildContainer, []);
  return <ApiContext.Provider value={container}>{children}</ApiContext.Provider>;
}

export function useApis(): ApiContainer {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error("useApis must be used within ApiProvider");
  return ctx;
}
