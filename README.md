# CATCHUP

**Catchup remembers what the market looked like when you last checked — and
tells you what meaningfully changed when you return.**

It is an *attention inbox* for a stock watchlist, not a dashboard:

```
WHAT CHANGED → WHY IT STANDS OUT → THE EVIDENCE → RAW DATA
```

Every number you see is real data from a live market-data pipeline (Yahoo
Finance via a provider adapter) that the ingestion worker writes asynchronously.
Nothing on screen is fabricated — when there is no data yet, the app says so
explicitly instead of inventing a number.

---

## Repositories

| Directory | What it is |
| --- | --- |
| `backend/` | Python 3.11+ FastAPI modular monolith — ingestion worker, signal detection, personalization, HTTP API. |
| `catchup-frontend/` | React 18 + TypeScript + Vite + Tailwind SPA. |

## The product loop

1. **Explore** (`/`) — real discovery: the top movers, dippers, and unusual
   activity across a curated *discovery universe*, filterable by sector. The
   sector chip scopes the underlying backend query — it is never a client-side
   filter.
2. **Search** — real catalog search by symbol or company. Stocks already in
   your watchlist are filtered out of results.
3. **Watchlist (Catchup)** (`/watchlist`) — your watchlist plus *what changed
   since your last check*: ranked changes with significance (
   `NORMAL → NOTABLE → SIGNIFICANT → CRITICAL`), why each change stands out, the
   evidence, and the raw data it came from.
4. **Stock detail** (`/stock/:id`) — the full picture for one stock: what
   changed, why, market-context, and an evidence panel with plain-language
   explanations and tiny visualizations (z-score against its own history,
   today's volume vs. typical volume).

## Honesty guarantees

- **No mock data in production.** Mock APIs exist only for local development
  (`VITE_API_MODE=mock`, which is also what the dev server defaults to for a
  backend-free demo). A production build refuses to boot without a real API
  configuration and shows an explicit configuration error instead of quietly
  serving fake market data.
- **Empty ≠ broken.** New users start with an empty watchlist. A sector without
  valid observations shows *"No {sector} stocks have valid market data right
  now"*, and a cold-start watchlist shows *"Baseline being established"* — the
  UI never fills gaps with invented values.
- **Significance is objective; relevance is context.** Significance tiers come
  purely from price/volume mathematics. Personalization is a composition-based
  summary of your actual watchlist (e.g. which sector it skews toward) — never
  a substitute that could hide a CRITICAL event.
- **Freshness is displayed, not faked.** Each data point carries a
  `DataStatus` (`LIVE / DELAYED / STALE / UNAVAILABLE`) and an observed-at
  timestamp; provider unavailability is surfaced as an alert, not papered over.

## What changed this round

- **Sector filtering is real** — `GET /instruments/explore?sector=IT` scopes
  the discovery query server-side (movers/dippers/unusual computed from exactly
  that sector) while the filter chips still list the full universe.
- **Daily vs. intraday baselines** — the historical baseline used for anomaly
  detection excludes partial in-progress sessions, so a live intraday move is
  compared against *completed* sessions only. Live quotes now report cumulative
  session volume for a fair comparison against the daily average.
- **Personalization stays honest** — composition-based relevance only; a fresh
  user gets no neutral "summary" fallback that could mask a real event.
- **Discovery universe balanced** — 25 instruments across sectors (banks,
  energy, IT, consumer, healthcare, autos, global tech).
- **Light/dark theme** — centralized CSS-variable tokens; dark mode is pure
  presentation and never changes product logic. Your choice is remembered
  (`localStorage`) and follows your OS preference until you override it.
- **Compact onboarding** — a small first-visit welcome box, a single clear
  "Add a stock" action, and no duplicate CTAs.
- **Evidence you can read** — the raw-data panel now explains each metric in
  plain language and draws tiny visualizations (z-score gauge, volume bars).

---

## Quick start (frontend only, mock mode)

No backend required — this runs the full experience against in-memory fixtures.

```bash
cd catchup-frontend
npm install
npm run dev        # http://localhost:5173
```

A dev-only scenario switcher (bottom-right) lets you preview feed states:
default, first visit, market closed, no changes, API down. It never renders in
production builds or while connected to a real API.

## Quick start (full stack, real data)

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
cp .env.example .env              # fill DATABASE_URL, SESSION_SECRET, CORS_ORIGINS
alembic upgrade head
```

Prepare data and run ingestion:

```bash
python -m app.infrastructure.scheduler.worker        # periodic ingestion (own process)
```

Add symbols through the UI (above), or run a one-off pass for a canonical
instrument id:

```bash
python -c "import sys; sys.path.insert(0,'.'); from app.infrastructure.scheduler.worker import run_once; run_once(['TCS','INFY','HDFCBANK'])"
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000            # docs at /docs
```

### 2. Frontend → real API

```bash
cd catchup-frontend
# .env (create if missing):
#   VITE_API_BASE_URL=http://localhost:8000
#   VITE_API_MODE=http
npm install
npm run dev
```

> **Production note:** mock mode is a dev convenience. Production builds
> require `VITE_API_MODE=http` and `VITE_API_BASE_URL`; without them CATCHUP
> shows a configuration error rather than serving fabricated data.

## Tests

Backend (fast, in-memory fakes — no DB or network):

```bash
cd backend
python -m pytest
```

Backend (optional Postgres integration, requires Docker):

```powershell
$env:CATCHUP_RUN_INTEGRATION=1
python -m pytest tests/integration -v
```

Frontend:

```bash
cd catchup-frontend
npm test
npm run build     # tsc typecheck + production bundle
```

The suites cover: baseline/z-score/volume math, significance classification,
corporate-event visibility, per-user last-seen diffing, provider
failure/no-data status transitions, daily-vs-intraday baseline exclusion,
sector-scoped explore queries, idempotent ingestion, the HTTP contract
(camelCase), sector refetch behavior, search watched-filtering, first-visit
onboarding, raw-data evidence, and theme behavior.

## Environment variables

Full documented set (with examples) in `backend/README.md`. Key ones:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string. |
| `CORS_ORIGINS` | Allowed frontend origins. |
| `SESSION_SECRET` | Signs session tokens — change in any deployed env. |
| `AUTH_REQUIRED` | `true` → token required for all requests. |
| `INGESTION_*` | Worker cadence, concurrency, enable/disable. |
| `STALE_* / DELAYED_*` | Freshness thresholds for `DataStatus`. |
| `BASELINE_*` | History window and sufficiency cut-offs. |
| `PRICE_* / VOLUME_*` | Significance thresholds (`NOTABLE / SIGNIFICANT / CRITICAL`). |

Frontend env vars (`catchup-frontend/.env`): `VITE_API_MODE` (`mock` default |
`http`), `VITE_API_BASE_URL`.

## Architecture

```
backend/
  app/
    domain/          # entities, enums, repository ports — no dependencies
    application/     # catchup, watchlist, instrument, explore, ingestion, market clock
    analytics/       # returns, baseline, z-score, volume, significance thresholds
    relevance/       # what-to-show-first ranking
    market_data/     # provider port + Yahoo Finance adapter + instrument catalog
    infrastructure/  # SQLAlchemy models, Postgres repositories, scheduler worker
    api/             # FastAPI routes, schemas, mappers, DI wiring
    main.py          # entrypoint
  tests/             # pytest (in-memory) + tests/integration (Docker Postgres)

catchup-frontend/
  src/
    app/             # providers (API selection, theme), layout, routes
    pages/           # Explore, Watchlist/Catchup, Stock detail
    components/      # presentational components (search, explorer, change feed …)
    api/             # interfaces + HTTP implementations (clients.ts)
    mocks/           # dev-only fixtures (never reachable in production builds)
    domain/          # the frontend/backend contract (domain/types.ts)
    tests/           # vitest + Testing Library
```

Two rules keep the frontend honest:

- **Components never call `fetch`.** They call interface methods via
  `useApis()`; `ApiProvider` selects mock (dev) or HTTP (prod) by config.
- **The backend owns all business logic.** The frontend renders contract values
  and explanations only — it derives nothing.

## Honesty, status

`MarketStatus` (`OPEN / CLOSED / UNKNOWN`) comes from the backend's
exchange-calendar, and `ProviderStatus` (`AVAILABLE / DEGRADED / UNAVAILABLE`)
from the ingestion heartbeat. Both are rendered as-is, so "the market is
closed" reads differently from "the data provider is down".