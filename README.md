# CATCHUP

**Catchup remembers what the market looked like when you last checked and tells
you what meaningfully changed when you return.** It is an attention inbox for a
stock watchlist.

The project has two parts:

| Directory | What it is |
| --- | --- |
| `backend/` | Python 3.13 FastAPI app: ingestion worker (Yahoo Finance), signal detection, personalization, HTTP API, PostgreSQL. |
| `catchup-frontend/` | React 18 + TypeScript + Vite + Tailwind single-page app. |

---

## Table of contents

- [Two ways to run it](#two-ways-to-run-it)
- [Option A — Frontend only, mock data (easiest)](#option-a--frontend-only-mock-data-easiest)
- [Option B — Full stack with real market data](#option-b--full-stack-with-real-market-data)
  - [1. Backend setup](#1-backend-setup)
  - [2. Database schema](#2-database-schema)
  - [3. Ingestion worker](#3-ingestion-worker)
  - [4. Run the API](#4-run-the-api)
  - [5. Frontend → real API](#5-frontend--real-api)
- [Tests](#tests)
- [Environment variables](#environment-variables)
- [How honest is the data?](#how-honest-is-the-data)
- [Project architecture](#project-architecture)

## Two ways to run it

- **Option A: mock mode.** No backend, no database, no network. The UI runs
  against in-memory fixtures so you can walk the whole product in minutes.
  **The numbers are simulated** — this is for evaluation/development only, and
  a production build will refuse to boot this way.
- **Option B: real mode.** Full stack against the real backend and a real
  market-data provider. This is what a real deployment looks like, and it is
  the only mode a production build accepts.

---

## Option A — Frontend only, mock data (easiest)

Requirements: Node.js (any recent LTS).

```bash
cd catchup-frontend
npm install
npm run dev
```

Open http://localhost:5173. Mock mode is the default (`VITE_API_MODE=mock`), so
no `.env` or backend is needed.

In dev + mock mode only, a small scenario switcher appears at the bottom-right
to preview different feed states (first visit, market closed, no changes, API
down). It is removed from production builds.

---

## Option B — Full stack with real market data

Requirements:

- Node.js (any recent LTS)
- Python 3.13 (see `backend/runtime.txt`)
- PostgreSQL (local install or a managed Supabase project)
- Working network access to Yahoo Finance (the provider endpoint)

> **Honest caveat before you start:** market data only exists in the database
> after the ingestion worker successfully pulls a trading session. If you set
> this up on a weekend or a holiday, the provider times out and pages honestly
> show empty states ("Awaiting first market data"). That is the app working as
> designed — it never fabricates numbers.

### 1. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env` from the example and edit at least `DATABASE_URL`,
`SESSION_SECRET`, and `CORS_ORIGINS`:

```bash
copy .env.example .env            # Windows
cp .env.example .env              # macOS/Linux
```

`.env` is git-ignored; you must create it yourself. The app reads it
automatically from the `backend/` directory (pydantic-settings).

Example `DATABASE_URL` for a local Postgres:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/catchup
```

### 2. Database schema

```bash
cd backend
alembic upgrade head
```

`alembic/env.py` loads the connection string from your `.env`, so this uses the
same `DATABASE_URL`. The migrations create all tables; nothing else to set up.

### 3. Ingestion worker

The worker is a separate process that polls the provider and writes snapshots
and signals. The API never calls the provider on demand it reads whatever the
worker has already persisted.

Periodic loop (run in its own terminal):

```bash
cd backend
python -m app.infrastructure.scheduler.worker
```

By default it ingests the instruments in your watchlist. To ingest a specific
set of discovery-catalog symbols right now (for example, so the Explore page
has data), run a one-off pass:

```bash
cd backend
python -c "import sys; sys.path.insert(0,'.'); from app.infrastructure.scheduler.worker import run_once; run_once(['TCS','INFY','RELIANCE'])"
```

> `run_once` uses canonical instrument ids from the catalog
> (`backend/app/market_data/catalog.py`), not Yahoo suffixes.

### 4. Run the API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health (verifies app + database)

### 5. Frontend → real API

```bash
cd catchup-frontend
```

Create `catchup-frontend/.env` (also git-ignored):

```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_MODE=http
```

Then:

```bash
npm install
npm run dev
```

After you have the worker saving snapshots, add a few stocks from the UI (or a
`run_once` pass), and the app will show real movers, changes, and evidence.

> **Production note:** production builds (`npm run build`) require
> `VITE_API_MODE=http` and `VITE_API_BASE_URL`. Without them CATCHUP shows a
> configuration error instead of starting — it will not serve mock data in a
> production build.

---

## Tests

Backend (fast, in-memory fakes — no database or network):

```bash
cd backend
python -m pytest
```

Backend (optional Postgres integration tests — requires Docker):

```powershell
$env:CATCHUP_RUN_INTEGRATION=1
python -m pytest tests/integration -v
```

Frontend:

```bash
cd catchup-frontend
npm test
npm run build        # runs tsc typecheck + production bundle
```

Current suite: backend `pytest` (176 tests) and frontend vitest (36 tests) +
clean `tsc`.

---

## Environment variables

Backend (`backend/.env`) — see `backend/.env.example` for the full list with
examples. The important ones:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://postgres:postgres@localhost:5432/catchup` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173,http://127.0.0.1:5173` |
| `SESSION_SECRET` | Signs session tokens — change in any deployed env | `dev-only-secret-change-me` |
| `AUTH_REQUIRED` | `true` → all requests need a session token | `false` |
| `INGESTION_ENABLED` | Whether the periodic worker loop runs | `false` |
| `INGESTION_INTERVAL_SECONDS` | Quote polling interval | `300` |
| `STALE_THRESHOLD_MINUTES` / `DELAYED_THRESHOLD_MINUTES` | Freshness → `DataStatus` | `30` / `5` |
| `BASELINE_WINDOW_DAYS` & `MIN_BASELINE_RETURNS` | History window & baseline sufficiency | `30` / `20` |
| `PRICE_*` / `PRICE_*_Z` / `VOLUME_*` | Significance thresholds (`NOTABLE/SIGNIFICANT/CRITICAL`) | see `.env.example` |

Frontend (`catchup-frontend/.env`):

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_MODE` | `mock` (dev only) or `http` (real backend) | `mock` |
| `VITE_API_BASE_URL` | Backend base URL, e.g. `http://localhost:8000` | *(empty)* |

There is exactly one curated constant in application code: the discovery
catalog (`DISCOVERY_SYMBOLS` in `backend/app/market_data/catalog.py`), which is
the bounded universe the Explore page samples from and where `run_once` ids come
from. Everything environment-specific — database URL, CORS origins, polling
interval, freshness thresholds, significance thresholds — is configuration read
from `.env` with code defaults for local development, and the frontend chooses
its mode entirely from `.env` (`VITE_API_MODE` / `VITE_API_BASE_URL`).

---

## How honest is the data?

- **No mock data in production.** Mocks exist only for local development.
- **Empty ≠ broken.** A new user starts with an empty watchlist. A sector
  without valid observations says *"No {sector} stocks have valid market data
  right now"*, and a brand-new stock says *"Baseline being established"*. No
  gap is filled with an invented number.
- **Significance is math; relevance is context.** Significance tiers
  (`NORMAL → NOTABLE → SIGNIFICANT → CRITICAL`) come purely from price/volume
  statistics. Personalization is a composition-based summary of your actual
  watchlist (e.g. which sector it skews toward) and can never hide a CRITICAL
  event behind a "just for you" summary.
- **Freshness is shown, not faked.** Every data point carries an observed-at
  timestamp and a `DataStatus` (`LIVE / DELAYED / STALE / UNAVAILABLE`).
  Provider outages surface as an alert, and the market clock is real — on a
  weekend the app says the market is closed.
- **Baselines are only built from completed sessions.** A partial in-progress
  trading day never enters the historical baseline, so live moves are compared
  against finished sessions only.

## Project architecture

```
backend/
  app/
    domain/          # entities, enums, repository ports (no dependencies)
    application/     # catchup, watchlist, instrument, explore, ingestion, market clock
    analytics/       # returns, baseline, z-score, volume, significance thresholds
    relevance/       # what-to-show-first ranking
    market_data/     # provider port + Yahoo Finance adapter + instrument catalog
    infrastructure/  # SQLAlchemy models, Postgres repositories, scheduler worker
    api/             # FastAPI routes, schemas, mappers, DI wiring
    main.py          # entrypoint
  tests/             # pytest (in-memory) + tests/integration (Docker Postgres)
  alembic/           # database migrations

catchup-frontend/
  src/
    app/             # providers (API selection, theme), layout, routes
    pages/           # Explore, Watchlist/Catchup, Stock detail
    components/      # presentational components (search, explorer, change feed …)
    api/             # API interfaces + HTTP implementations (clients.ts)
    mocks/           # dev-only fixtures
    domain/          # frontend/backend contract (domain/types.ts)
    tests/           # vitest + Testing Library
```

Two rules keep the frontend honest:

- Components never call `fetch`. They call interface methods via `useApis()`;
  `ApiProvider` selects mock (dev) or HTTP (prod) by configuration.
- The backend owns all business logic. The frontend renders contract values and
  explanations only — it derives nothing.