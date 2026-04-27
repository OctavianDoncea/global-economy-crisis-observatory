# Global Economic Crisis Observatory

> An end-to-end data platform that ingests global macroeconomic data, detects crisis signals using machine learning, scores news sentiment, and serves insights through an interactive dashboard.

[![CI](https://github.com/YOUR_USERNAME/global-economic-observatory/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/global-economic-observatory/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What this project demonstrates

| Layer | Tech | Why |
|---|---|---|
| **Orchestration** | Apache Airflow 2.10 (LocalExecutor) | Industry-standard scheduling with retries, SLAs, and alerting |
| **Ingestion** | Python 3.11, httpx, tenacity | Idempotent clients with exponential backoff retry |
| **Validation** | Pandera | Type-safe DataFrame contracts before data hits the warehouse |
| **Storage** | PostgreSQL 16 | Production-grade relational warehouse |
| **Transformation** | dbt Core | Star-schema models with full lineage and tests |
| **ML / Stats** | scikit-learn, statsmodels | Anomaly detection, forecasting, hypothesis testing |
| **NLP** | VADER, spaCy | Sentiment scoring on financial news |
| **Visualization** | Apache Superset | Public, interactive dashboard |
| **Quality** | Pre-commit, ruff, black, pytest, GitHub Actions | Production code hygiene |
| **Deployment** | Docker Compose | Single-command local stack |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES (free)                            │
│   FRED API   │  World Bank API  │  yfinance  │   GDELT (no key)        │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────┐
│   INGESTION (Python)        │  ──── orchestrated by ────►  Apache Airflow
│   - Idempotent upserts      │                              (DAGs, retries,
│   - Pandera validation      │                               Slack alerts)
│   - Tenacity retries        │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  RAW STORAGE (PostgreSQL)   │  schema: raw.*
│  - 4 source tables + audit  │
└──────────┬──────────────────┘
           │
           ▼ (Phase 2)
┌─────────────────────────────┐
│  TRANSFORMATION (dbt)       │  schema: staging.* → marts.*
│  - Star schema              │
│  - Tests + lineage docs     │
└──────────┬──────────────────┘
           │
           ▼ (Phase 3)
┌─────────────────────────────┐
│  ML + NLP                   │
│  - Isolation Forest         │
│  - Sentiment scoring        │
│  - Hypothesis testing       │
└──────────┬──────────────────┘
           │
           ▼ (Phase 4)
┌─────────────────────────────┐
│  SERVING (Apache Superset)  │
└─────────────────────────────┘
```

## Quick start

### Prerequisites

- Docker Desktop 4.x or Docker Engine 24+ with Docker Compose
- Python 3.11 (for local development; not required if you only use Docker)
- A free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) (60 seconds to register)

### One-time setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/YOUR_USERNAME/global-economic-observatory.git
cd global-economic-observatory

# 2. Create your environment file and fill in FRED_API_KEY
cp .env.example .env
${EDITOR:-nano} .env

# 3. Start everything
make up
```

After ~2 minutes you'll have:
- PostgreSQL on `localhost:5432` (user: `postgres`, password: `postgres`)
- Airflow UI on http://localhost:8080 (user: `admin`, password: `admin`)

### Trigger your first ingestion

```bash
# Either through Airflow UI: enable and run weekly_macro_indicators

# Or run directly via Python:
make setup       # creates .venv with dependencies
make ingest-fred
```

### Inspect the data

```bash
make psql
# Then in psql:
\dt raw.*
SELECT series_id, COUNT(*) FROM raw.fred_observations GROUP BY 1 ORDER BY 1;
SELECT * FROM raw.ingestion_runs ORDER BY started_at DESC LIMIT 10;
```

## Common commands

```bash
make help            # Show all available commands
make up              # Start the Docker stack
make down            # Stop everything
make logs            # Tail logs
make psql            # Open a psql shell
make ingest-all      # Run every ingestor once
make test            # Run unit tests
make lint            # Run ruff + black checks
make format          # Auto-format with ruff + black
```

## Data sources

All sources are completely free — no paid tiers, no credit card.

| Source | Auth | Rate limit |
|---|---|---|
| [FRED](https://fred.stlouisfed.org/docs/api/) | Free key | 120 req/min |
| [World Bank Open Data](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | None | None practical |
| [yfinance](https://github.com/ranaroussi/yfinance) | None | Be polite |
| [GDELT 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) | None | None practical |

## License

MIT. See [LICENSE](LICENSE).