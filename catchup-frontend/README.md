# CATCHUP — Frontend

**Catchup remembers what the market looked like when you last checked and tells
you what meaningfully changed when you return.** It is an attention inbox for a
watchlist, not a stock dashboard:

```
WHAT CHANGED → WHY IT STANDS OUT → THE EVIDENCE → RAW DATA
```

## Architecture

    UI (pages / components)
        ↓ depends on
    API interfaces (src/api/exploreApi.ts, watchlistApi.ts, catchupApi.ts)
        ↓ satisfied by (selected in app/providers/ApiProvider.tsx)
    Mock API (src/mocks/)  │  Http API (src/api/httpClients.ts)
                          │      ↓
                          │   FastAPI backend (market provider, DB, signals)

Key rules:

- **Components never call fetch.** They call interface methods via `useApis()`.
- **The backend owns all business logic** (anomaly detection, z-scores,
  significance, baselines). The frontend renders contract values and
  explanations only — it derives nothing.
- **Mocks are dev-only.** Mock mode is the default for a backend-free demo,
  but a production build refuses to start without `VITE_API_MODE=http` +
  `VITE_API_BASE_URL`. It shows an explicit configuration error rather than
  serving fabricated market data. The scenario switcher renders only in dev +
  mock mode.
- Swapping `mock → HTTP` means setting `VITE_API_MODE=http` and
  `VITE_API_BASE_URL`; `ApiProvider` selects the implementation. No UI changes.

## Domain models

All contracts live in `src/domain/types.ts`: `Instrument`, `WatchlistItem`,
`MarketSnapshot`, `ChangeSignal`, `ChangeDetail`, `CatchupFeed`, `Explore`,
plus unions for `SignificanceTier`, `DataStatus`, `MarketStatus`,
`ProviderStatus`, `ChangeEventType`.

## Pages

- **Explore** (`/`) — movers / dippers / unusual across the discovery universe.
  Sector chips refetch `GET /instruments/explore?sector=…` so the query is
  genuinely scoped server-side. Search filters out already-watched stocks.
- **Catchup / Watchlist** (`/watchlist`) — ranked changes since your last check
  plus personalization summary; a compact welcome box on first visit.
- **Stock detail** (`/stock/:id`) — what changed, why, evidence panel with
  plain-language metric explanations and tiny visualizations (z-score gauge,
  today-vs-typical volume bars, day range).

## Theme

Centralized CSS-variable tokens in `src/app/providers/theme.css` (light
`:root`, dark `.dark`), wired to Tailwind in `tailwind.config.js`. Choice is
stored in `localStorage` (`catchup-theme`), follows the OS preference until
overridden, and is applied before first paint via an inline script in
`index.html`. Theme is pure presentation — it never changes product logic and
no component sprinkles `dark:` variants.

## Environment

Copy `.env.example` to `.env` (or export in CI):

- `VITE_API_BASE_URL` — backend base URL (no hardcoded localhost in code)
- `VITE_API_MODE` — `mock` (default, dev only) or `http`

## Run

    npm install
    npm run dev

## Test

    npm test
    npm run build     # tsc -b typecheck + production bundle

Tests cover: explore sections and per-sector refetch, honest empty states,
sector search behavior, watched-stock filtering, first-visit onboarding and
single-CTA, watchlist add/remove/failure/add-by-symbol, change-card rendering
and significance tiers, stale/unavailable display, the raw-data evidence panel,
and theme toggling/persistence.