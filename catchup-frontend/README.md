# Catchup — Frontend

**Catchup remembers what the market looked like when you last checked and tells
you what meaningfully changed when you return.**

It is an attention inbox for a watchlist, not a stock dashboard:

    WHAT CHANGED → WHY IT STANDS OUT → THE EVIDENCE → RAW DATA

## Architecture

    UI (pages / components)
        ↓ depends on
    Catchup API interfaces (api/catchupApi.ts, watchlistApi.ts, instrumentApi.ts)
        ↓ satisfied by (selected in app/providers/ApiProvider.tsx)
    Mock API (mocks/)          →   later: Http API (api/ + VITE_API_BASE_URL)
                                       →  FastAPI backend
                                          →  domain services / market provider / db

Key rules:

- **Components never call fetch.** They call interface methods via `useApis()`.
- **The backend owns all business logic** (anomaly detection, z-scores,
  significance, baselines). The frontend renders contract values only.
- **The mock layer is isolated** in `src/mocks/` and never imported by API
  interface definitions.
- Swapping `mock → HTTP` means implementing the same interfaces in
  `api/` and flipping `VITE_API_MODE=http` in `ApiProvider`. No UI changes.

## Domain models

All contracts live in `src/domain/types.ts`: `Instrument`, `WatchlistItem`,
`MarketSnapshot`, `ChangeSignal`, `ChangeDetail`, `CatchupFeed`, plus unions
for `SignificanceTier`, `DataStatus`, `MarketStatus`, `ProviderStatus`,
`ChangeEventType`.

## Mock API

`mockData.ts` holds pure representative values (no formulas). The mock APIs
add latency and cover: price anomaly, volume anomaly, corporate event,
unchanged, stale, unavailable, market closed, first visit, insufficient
baseline, and API-down scenarios (`setMockScenario` / demo switcher).

## Connecting the backend later

1. Implement `CatchupApi`, `WatchlistApi`, `InstrumentApi` over HTTP in
   `src/api/` using `httpJson()` from `client.ts`.
2. Register them in `ApiProvider.buildContainer()` when
   `apiConfig.mode === "http"`.
3. Done. Pages and components are untouched.

## Environment

Copy `.env.example` to `.env`:

- `VITE_API_BASE_URL` — backend base URL (no hardcoded localhost in code)
- `VITE_API_MODE` — `mock` (default) or `http`

## Run

    npm install
    npm run dev

## Test

    npm test

Tests cover: change card rendering, significance tiers, stale/unavailable
display, empty watchlist, API failure, add/remove via API abstraction, and the
raw-data evidence panel.
