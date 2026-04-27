# Architecture

## Goals

1. **Idempotency** — every ingestion job can be re-run safely; primary keys + upserts guarantee no duplicates
2. **Observability** — every run is logged in `raw.ingestion_runs`; Airflow UI shows DAG state; logs go to stderr in dev, structured in Airflow
3. **Quality gates** — Pandera schemas validate DataFrames before they hit PostgreSQL; dbt tests will gate the staging→marts transition
4. **Cheap to run** — entire stack runs in Docker on a laptop; production-grade pieces (Airflow, dbt, PostgreSQL) used in their open-source forms
5. **Cheap to extend** — adding a new data source means subclassing `BaseIngestor` and writing one DAG file

## Layered storage

| Layer | Owner | Materialization | Purpose |
|---|---|---|---|
| `raw` | Python ingestion clients | Tables with PK | Mirrors source structure; append-or-upsert only |
| `staging` | dbt | Views | Cleaned, typed, deduplicated. One model per raw table. |
| `marts` | dbt | Tables | Star schema. Business-facing facts and dimensions. |

This is the standard analytics-engineering layering popularised by [dbt](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview). It separates concerns — Python handles "get the data in", SQL handles "make the data make sense" — and gives every consumer (dashboards, ML, ad-hoc analysis) a clean, tested model to query.

## Why these choices

### PostgreSQL over SQLite or DuckDB
- We need an Airflow metadata DB anyway, so a single PostgreSQL serves both
- Multi-user access is needed for Superset connection
- Patterns (schemas, JSONB, window functions) translate directly to BigQuery/Snowflake

### Airflow LocalExecutor over CeleryExecutor
- Personal-project scale doesn't need distributed workers
- One-process scheduling is simpler to debug
- Migrating to Celery later is a config change, not an architecture change

### dbt Core over scripted SQL
- Free and self-hosted (no dbt Cloud needed)
- Native testing framework
- Auto-generated lineage docs as portfolio asset
- Industry standard — naming this on a CV is what matters

### Pandera over Great Expectations (for now)
- ~80% of the value with ~20% of the dependency surface
- Easier to use mid-pipeline (`schema.validate(df)`)
- We can layer Great Expectations on top in Phase 5 for the CV cred

### GDELT over GNews
- No API key, no rate limits to hit during testing
- Massive corpus (covers most of the global news web)
- Trade-off: noisier metadata than a curated commercial API

## Idempotency strategy

Every raw table has a natural primary key (e.g. `(series_id, obs_date)` for FRED). Ingestion uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE`, implemented in `src/utils/db.py::upsert_df`. Re-running a DAG run produces the same final database state.

The `fetched_at` column is updated on every upsert, so we can tell when a row was last refreshed without losing the original load timestamp (which lives in the audit log).

## Failure handling

Three layers:

1. **HTTP retries** — `tenacity` retries transient errors (timeouts, 5xx) with exponential backoff, up to 3 attempts per request
2. **Airflow task retries** — DAG-level retries with their own exponential backoff, so a flaky API outage that exceeds the per-call retry doesn't fail the run
3. **Run logging** — every attempt is recorded in `raw.ingestion_runs` with status (`running`/`success`/`failed`) and error message, so post-mortem is easy

Slack alerting is wired up but optional — set `SLACK_WEBHOOK_URL` in `.env` to enable it.

## Decisions deferred

- **Cloud deployment** — local-only for now. Phase 5 will document a deployment path (Render free tier or a single GCP VM).
- **Schema evolution** — currently handled by editing migration SQL and rebuilding the volume. Alembic is overkill at this stage.
- **CDC / streaming** — batch-only. No use case yet for sub-hourly latency.
- **Testing the DAGs themselves** — Phase 1 covers unit tests for ingestion clients. Airflow DAG integration tests (using the `airflow tasks test` CLI) come in Phase 2.