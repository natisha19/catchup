# Catchup Backend — Architecture

## Layering

Dependency arrows point one way only:

```
api  →  application  →  domain(interfaces)
          ↓
    analytics / relevance / market_data   (pure, framework-free)
          ↓
    infrastructure (SQLAlchemy, Postgres repos, provider adapters)
```

- **domain** — dataclasses + enums + repository *Protocols*. No FastAPI, no
  SQLAlchemy, no provider SDK.
- **application** — services (`CatchupService`, `WatchlistService`,
  `IngestionService`) that orchestrate repositories and pure analytics.
- **analytics / relevance / market_data** — framework-free, easily unit-tested.
- **infrastructure** — concrete SQLAlchemy models, Postgres repositories, the
  yfinance adapter, and the ingestion scheduler.
- **api** — thin routes; all construction happens in `app/api/deps.py`
  (composition root).

## Key decisions (ADRs)

### ADR-001 — Modular monolith, not microservices
One deployable with clear internal boundaries. The domain is where the product
lives; databases/providers are swappable adapters.

### ADR-002 — Provider behind a port
`MarketDataProvider` (in `app/market_data/provider.py`) is the only place the
rest of the system knows about a source. `YahooFinanceProvider` is today's
implementation; swapping sources touches no analytics or API code.

### ADR-003 — Domain dataclasses everywhere; no ORM leakage
Services never see a `Session` or a `Model`. They depend on repository
*Protocols* and exchange plain dataclasses. Infrastructure maps to/from them.

### ADR-004 — Baseline never self-contaminates
The current observation is excluded from its own baseline. Sufficiency is
strict: `SUFFICIENT` (>= MIN), `LIMITED` (>= LIMITED, z may be usable),
`UNAVAILABLE` (never invent a z-score).

### ADR-005 — Significance is deterministic and rule-based
Tiers and reason codes come from configured thresholds + a fixed combine
function, so behavior is reproducible and auditable. A statistical/ML ranker can
slot in behind the `RelevanceRanker`/signature seams later.

### ADR-006 — Freshness is explicit
`DataStatus` (`LIVE/DELAYED/STALE/UNAVAILABLE`) is stored on every snapshot.
A provider failure demotes the last validated snapshot to `STALE`; the absence
of any data reports `UNAVAILABLE`. The frontend contract maps these into its own
baseline/data status view.

### ADR-007 — Ingestion is a separate worker
The API is decoupled from provider availability/network. A long-running worker
(`app/infrastructure/scheduler/worker.py`) pulls data on an interval and writes
snapshots + signals. The API only reads.

### ADR-008 — Idempotent ingestion + per-user last-seen
Snapshots are deduped by `(instrument_id, observed_at, source)` and signals by
`(instrument_id, observed_at)` so re-ingestion never duplicates rows. Catchup
visibility is computed per `(user_id, instrument_id)` last-seen snapshot — a
generated signal does not imply the user saw it.

### ADR-009 — API is the frontend contract
`app/api/schemas.py` is authored to mirror the existing React types exactly
(camelCase JSON). `app/api/mappers.py` enriches signals with symbol/company and
maps baseline status to the frontend's `READY`/`INSUFFICIENT`.
