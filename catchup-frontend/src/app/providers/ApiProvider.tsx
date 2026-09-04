import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { CatchupApi } from "../../api/catchupApi";
import type { InstrumentApi, WatchlistApi } from "../../api/watchlistApi";
import { apiConfig, ensureSession } from "../../api/clients";
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
  const needsSession = apiConfig.mode === "http" && Boolean(apiConfig.baseUrl);
  const [sessionReady, setSessionReady] = useState(!needsSession);

  // In http mode, mint a signed session before mounting request-making pages.
  // Without this gate, AUTH_REQUIRED deployments can race their first feed
  // request against session creation and render a misleading 401 error.
  useEffect(() => {
    if (!needsSession) return;
    void ensureSession().finally(() => setSessionReady(true));
  }, [needsSession]);

  if (!sessionReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper text-sm text-ink-muted" role="status">
        Preparing your secure watchlist…
      </div>
    );
  }

  return <ApiContext.Provider value={container}>{children}</ApiContext.Provider>;
}

export function useApis(): ApiContainer {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error("useApis must be used within ApiProvider");
  return ctx;
}
