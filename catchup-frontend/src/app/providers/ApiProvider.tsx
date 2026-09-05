import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { CatchupApi } from "../../api/catchupApi";
import type { ExploreApi } from "../../api/exploreApi";
import type { InstrumentApi, WatchlistApi } from "../../api/watchlistApi";
import { apiConfig, ensureSession } from "../../api/clients";
import {
  HttpCatchupApi,
  HttpExploreApi,
  HttpInstrumentApi,
  HttpWatchlistApi,
} from "../../api/httpClients";
import { mockCatchupApi } from "../../mocks/mockCatchupApi";
import { mockExploreApi } from "../../mocks/mockExploreApi";
import { mockWatchlistApi, mockInstrumentApi } from "../../mocks/mockWatchlistApi";

export interface ApiContainer {
  catchup: CatchupApi;
  watchlist: WatchlistApi;
  instrument: InstrumentApi;
  explore: ExploreApi;
}

// Select implementation based on configuration only. Components never do.
// Mock mode is a development convenience: a production artifact is never
// allowed to silently serve fabricated market data.
function buildContainer(): ApiContainer {
  if ((apiConfig.mode === "http" || import.meta.env.PROD) && apiConfig.baseUrl) {
    return {
      catchup: new HttpCatchupApi(),
      watchlist: new HttpWatchlistApi(),
      instrument: new HttpInstrumentApi(),
      explore: new HttpExploreApi(),
    };
  }
  if (import.meta.env.PROD) {
    throw new Error(
      "CATCHUP is missing its API configuration. Set VITE_API_MODE=http and " +
        "VITE_API_BASE_URL when deploying — mock market data is disabled in production builds.",
    );
  }
  return {
    catchup: mockCatchupApi,
    watchlist: mockWatchlistApi,
    instrument: mockInstrumentApi,
    explore: mockExploreApi,
  };
}

const ApiContext = createContext<ApiContainer | null>(null);

export function ApiProvider({ children }: { children: ReactNode }) {
  // Resolve once up front; a misconfigured production build fails loudly with
  // a clear message instead of rendering fake market data.
  const [{ container, error }] = useState(() => {
    try {
      return { container: buildContainer(), error: null as string | null };
    } catch (e) {
      return { container: null, error: e instanceof Error ? e.message : String(e) };
    }
  });

  if (error) {
    return (
      <div
        role="alert"
        className="flex min-h-screen items-center justify-center bg-paper px-6"
      >
        <div className="card max-w-md p-6 text-sm leading-relaxed text-ink">
          <h1 className="text-base font-semibold">CATCHUP cannot start.</h1>
          <p className="mt-2 text-ink-muted">{error}</p>
        </div>
      </div>
    );
  }

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
