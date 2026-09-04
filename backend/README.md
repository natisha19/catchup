# Catchup — Backend

A Python 3.11+ FastAPI service behind the Catchup "attention inbox". It remembers
the market state each time a user checks and reports what meaningfully changed
when they come back.

Modular monolith: a clean **domain / application / infrastructure / api** split so
the market-data provider, the database, and the classification rules can each
change without touching the rest.

```
backend/
  app/
    domain/          # entities + enums + repository ports (no deps)
    application/     # services: catchup, watchlist, instrument, ingestion
    analytics/       # returns, baseline, z-score, volume, significance
    relevance/       # ranking of what to show first
    market_data/     # provider port + yfinance adapter + validation
    infrastructure/  # SQLAlchemy models + Postgres repos + scheduler
    api/             # FastAPI routes, schemas, mappers, DI wiring
    main.py          # app entrypoint
  tests/             # pytest suite (in-memory fakes; no DB/network needed)
  alembic/           # migrations
```

## Requirements

- Python 3.11+ (tested with 3.13)
- PostgreSQL (local or managed — a free Supabase project works)

## 1. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Create `backend/.env` from `.env.example` and fill in the values below.

### Backend `.env`

| Variable | Example | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/catchup` | Use your Postgres/Supabase connection string. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed frontend origins. |
| `PROVIDER_TIMEOUT_SECONDS` | `10` | per-request market-data timeout. |
| `PROVIDER_MAX_RETRIES` | `3` | retries with backoff before giving up. |
| `INGESTION_INTERVAL_SECONDS` | `300` | polling interval for the ingestion worker. |
| `INGESTION_ENABLED` | `true` | whether the background ingestion worker runs. |
| `STALE_THRESHOLD_MINUTES` | `30` | data older than this (during open market) is STALE. |
| `DELAYED_THRESHOLD_MINUTES` | `5` | quote age above this but below the stale threshold is DELAYED. |
| `BASELINE_WINDOW_DAYS` | `30` | historical window for the baseline. |
| `MIN_BASELINE_RETURNS` | `20` | points for a `SUFFICIENT` baseline. |
| `LIMITED_BASELINE_RETURNS` | `5` | points for a `LIMITED` baseline. |
| `PRICE_NOTABLE_THRESHOLD` | `2.0` | % return for NOTABLE. |
| `PRICE_SIGNIFICANT_THRESHOLD` | `4.0` | % return for SIGNIFICANT. |
| `PRICE_CRITICAL_THRESHOLD` | `7.0` | % return for CRITICAL. |
| `PRICE_NOTABLE_Z` | `1.5` | z-score for NOTABLE. |
| `PRICE_SIGNIFICANT_Z` | `2.0` | z-score for SIGNIFICANT. |
| `PRICE_CRITICAL_Z` | `3.0` | z-score for CRITICAL. |
| `VOLUME_NOTABLE_RATIO` | `2.0` | volume ratio (current / average) for NOTABLE. |
| `VOLUME_SIGNIFICANT_RATIO` | `3.0` | volume ratio for SIGNIFICANT. |
| `LOG_LEVEL` | `INFO` | |

## 2. Create the database schema

```bash
cd backend
alembic upgrade head
```

This applies the initial migration (7 tables) and records the version.

## 3. Add instruments + run ingestion

The product is driven by a watchlist. Seed a few symbols and keep data flowing
with the ingestion worker:

```bash
# One-off ingestion of specific symbols (bootstrap a watchlist + baselines)
python -c "import sys; sys.path.insert(0,'.'); from app.infrastructure.scheduler.worker import run_once; run_once(['TCS.NS','INFY.NS','HDFCBANK.NS'])"

# Or run the periodic worker (loop; run in its own terminal / process)
python -m app.infrastructure.scheduler.worker
```

Ingestion is intentionally decoupled from user requests: it runs as a separate
process. The API reads whatever data has already landed.

## 4. Run the API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive Swagger UI.
`GET /health` verifies app + database connectivity.

## 5. Frontend wiring

The frontend talks to this backend over HTTP. Create `catchup-frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_MODE=http
```

Frontend `VITE_API_MODE` values:
- `mock` (default) — no backend needed; uses in-memory fixtures.
- `http` — uses the real backend; `VITE_API_BASE_URL` must point at the API.

```bash
cd catchup-frontend
npm install
npm run dev
```

## Tests

Backend (no database or network required — uses in-memory fakes):

```bash
cd backend
python -m pytest tests/
```

Covers: return/z-score/volume math, baseline sufficiency, classification,
corporate-event visibility, per-user last-seen diffing, provider failure -> STALE,
no-data -> UNAVAILABLE, idempotent ingestion, and the HTTP contract (camelCase).

Frontend:

```bash
cd catchup-frontend
npm test
```

## Configuration model

All thresholds and environment-specific values are read in `app/config.py` from
environment variables (via `backend/.env`). Nothing in the codebase hardcodes an
environment-specific value.
