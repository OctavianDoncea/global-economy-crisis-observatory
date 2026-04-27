# Data Dictionary

This document describes every table and column in the Observatory warehouse. The `raw` schema is documented here; the `staging` and `marts` schemas will be auto-documented by `dbt docs generate` once Phase 2 lands.

## Schema overview

| Schema | Owner | Lifecycle |
|---|---|---|
| `raw` | Python ingestion (this repo) | Append-or-upsert. Source-shaped. |
| `staging` | dbt | Views, rebuilt on every `dbt run`. Cleaned and typed. |
| `marts` | dbt | Tables, rebuilt on every `dbt run`. Star schema. |

---

## `raw.fred_observations`

Time-series macroeconomic observations from the [FRED API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `series_id` | `VARCHAR(64)` | NO | FRED series identifier, e.g. `UNRATE`, `GDPC1`, `DGS10`. |
| `obs_date` | `DATE` | NO | Observation date (start of period for non-daily series). |
| `value` | `DOUBLE PRECISION` | YES | The observation. `NULL` where FRED returned `"."`. |
| `fetched_at` | `TIMESTAMPTZ` | NO | When this row was last upserted. |

**Primary key:** `(series_id, obs_date)`
**Default series:** `UNRATE`, `GDPC1`, `CPIAUCSL`, `DGS10`, `DGS2`, `T10Y2Y`, `FEDFUNDS`, `INDPRO`

---

## `raw.worldbank_indicators`

Annual development indicators from the [World Bank Open Data API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `country_iso` | `CHAR(3)` | NO | ISO 3166-1 alpha-3 country code. Aggregates (e.g. `EUU`) are filtered at ingest. |
| `indicator_code` | `VARCHAR(64)` | NO | World Bank indicator code, e.g. `NY.GDP.MKTP.CD`. |
| `obs_year` | `INTEGER` | NO | Calendar year of the observation. |
| `value` | `DOUBLE PRECISION` | YES | The indicator value. Units vary by indicator. |
| `fetched_at` | `TIMESTAMPTZ` | NO | When this row was last upserted. |

**Primary key:** `(country_iso, indicator_code, obs_year)`

**Default indicators:**

| Code | Description | Units |
|---|---|---|
| `NY.GDP.MKTP.CD` | GDP | Current US$ |
| `NY.GDP.MKTP.KD.ZG` | GDP growth | Annual % |
| `SL.UEM.TOTL.ZS` | Unemployment | % of labour force (modelled ILO) |
| `FP.CPI.TOTL.ZG` | Inflation, consumer prices | Annual % |
| `GC.DOD.TOTL.GD.ZS` | Central government debt | % of GDP |
| `NE.EXP.GNFS.ZS` | Exports of goods and services | % of GDP |
| `BN.CAB.XOKA.GD.ZS` | Current account balance | % of GDP |

**Default countries:** G20 + a handful of additional European economies (30 total). See `src/ingestion/worldbank_client.py::DEFAULT_COUNTRIES`.

---

## `raw.market_prices`

Daily OHLCV data from Yahoo Finance via the `yfinance` Python library.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `ticker` | `VARCHAR(16)` | NO | Yahoo Finance ticker symbol, e.g. `^GSPC`, `BTC-USD`. |
| `obs_date` | `DATE` | NO | Trading session date (UTC). |
| `open` | `DOUBLE PRECISION` | YES | Opening price. |
| `high` | `DOUBLE PRECISION` | YES | Session high. |
| `low` | `DOUBLE PRECISION` | YES | Session low. |
| `close` | `DOUBLE PRECISION` | YES | Closing price. |
| `adj_close` | `DOUBLE PRECISION` | YES | Dividend- and split-adjusted close. |
| `volume` | `BIGINT` | YES | Shares / contracts traded. |
| `fetched_at` | `TIMESTAMPTZ` | NO | When this row was last upserted. |

**Primary key:** `(ticker, obs_date)`

**Default tickers:** S&P 500 (`^GSPC`), NASDAQ (`^IXIC`), Dow (`^DJI`), FTSE 100 (`^FTSE`), DAX (`^GDAXI`), Nikkei 225 (`^N225`), Euro Stoxx 50 (`^STOXX50E`), VIX (`^VIX`), DXY (`DX-Y.NYB`), gold futures (`GC=F`), WTI crude (`CL=F`), Bitcoin (`BTC-USD`).

> **Note:** Yahoo data is fine for analytics but is not authoritative. For research that depends on tick-level accuracy, use a paid feed.

---

## `raw.news_articles`

Recent news articles from the [GDELT 2.0 Doc API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), filtered to a macroeconomic query.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `article_id` | `VARCHAR(64)` | NO | MD5 hash of the URL — stable, dedupes idempotently. |
| `published_at` | `TIMESTAMPTZ` | YES | When GDELT first saw the article (UTC). |
| `source_domain` | `VARCHAR(255)` | YES | Publisher domain, e.g. `reuters.com`. |
| `title` | `TEXT` | YES | Article headline. |
| `description` | `TEXT` | YES | Snippet. Empty for GDELT (it doesn't return one); reserved for future sources. |
| `url` | `TEXT` | NO | Canonical article URL. |
| `language` | `VARCHAR(8)` | YES | Article language as reported by GDELT. |
| `country_code` | `VARCHAR(8)` | YES | Source country as reported by GDELT. |
| `fetched_at` | `TIMESTAMPTZ` | NO | When this row was last upserted. |

**Primary key:** `(article_id)`

**Default query:**
```
(economy OR recession OR inflation OR "central bank" OR
 "interest rate" OR "yield curve" OR "financial crisis")
```

---

## `raw.ingestion_runs`

Audit log written by `src/utils/db.py::run_log`. Every ingestion attempt produces one row.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `run_id` | `BIGSERIAL` | NO | Auto-increment primary key. |
| `source` | `VARCHAR(64)` | NO | Source name from `BaseIngestor.source_name`. |
| `started_at` | `TIMESTAMPTZ` | NO | Wall-clock start time. |
| `finished_at` | `TIMESTAMPTZ` | YES | Wall-clock finish time. `NULL` while running. |
| `rows_inserted` | `INTEGER` | YES | Rows submitted to the upsert (not necessarily new rows). |
| `status` | `VARCHAR(16)` | NO | `running`, `success`, or `failed`. |
| `error_message` | `TEXT` | YES | First 1000 chars of the exception, if any. |
| `parameters` | `JSONB` | YES | The kwargs passed to `BaseIngestor.run()` for this attempt. |

**Useful queries:**

```sql
-- Recent runs by source
SELECT source, status, started_at, finished_at, rows_inserted
FROM raw.ingestion_runs
ORDER BY started_at DESC
LIMIT 20;

-- Failure rate over the last 7 days
SELECT source,
       COUNT(*) FILTER (WHERE status = 'failed') AS failed,
       COUNT(*)                                  AS total,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'failed') / COUNT(*), 1) AS pct_failed
FROM raw.ingestion_runs
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY source;

-- Average run duration by source
SELECT source,
       AVG(EXTRACT(EPOCH FROM (finished_at - started_at)))::INT AS avg_seconds
FROM raw.ingestion_runs
WHERE status = 'success'
GROUP BY source;
```