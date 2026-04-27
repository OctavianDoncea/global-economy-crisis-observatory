CREATE TABLE IF NOT EXISTS raw.fred_observations (
    seried_id  VARCHAR(64) NOT NULL,
    obs_date   DATE        NOT NULL,
    value      DOUBLE PRECISION,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (series_id, obs_data)
);
CREATE INDEX IF NOT EXISTS idx_fred_obs_date ON raw.fred_observations (obs_date);
CREATE INDEX IF NOT EXISTS idx_fred_obs_fetched ON raw.fred_observations (fetched_at);

COMMENT ON TABLE raw.fred_observations IS 'FRED time-series observations. Source: api.stlouisfed.org';
COMMENT ON COLUMN raw.fred_observations.series_id IS 'FRED series identifier, e.g. UNRATE, GDPC1, DGS10.';
COMMENT ON COLUMN raw.fred_observations.value IS 'Observed value. NULL where source returned ".".';

CREATE TABLE IF NOT EXISTS raw.worldbank_indicators (
    country_iso    CHAR(3)           NOT NULL,
    indicator_code VARCHAR(64)       NOT NULL,
    obs_year       INTEGER           NOT NULL,
    value          DOUBLE PRECISION,
    fetched_at     TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    PRIMARY KEY (country_iso, indicator_code, obs_year)
);
CREATE INDEX IF NOT EXISTS idx_wb_year ON raw.worldbank_indicators (obs_year);
VREATE INDEX IF NOT EXISTS idx_wb_indicator ON raw.worldbank_indicators (indicator_code);

COMMENT ON TABLE raw.worldbank_indicators IS 'World Bank annual indicators. Source: api.worldbank.org/v2';
COMMENT ON COLUMN raw.worldbank_indicators.country_iso IS 'ISO 3166-1 alpha-3 country code (or aggregate)';
COMMENT ON COLUMN raw.worldbank_indicators.indicator_code IS 'World Bank indicator code, e.g. NY.GDP.MKTP.CD';

CREATE TABLE IF NOT EXISTS raw.market_prices (
    ticker VARCHAR(16) NOT NULL,
    obs_date   DATE,
    open       DOUBLE PRECISION,
    high       DOUBLE PRECISION,
    low        DOUBLE PRECISION,
    close      DOUBLE PRECISION,
    adj_close  DOUBLE PRECISION,
    volume     BIGINT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, obs_date)
);
CREATE INDEX IF NOT EXISTS idx_market_date ON raw.market_prices (obs_date);

COMMENT ON TABLE raw.market_prices IS 'Daily OHLCV for indices and tickers. Source: yfinance';

CREATE TABLE IF NOT EXISTS raw.news_articles (
    article_id    VARCHAR(64) NOT NULL,
    published_at  TIMESTAMPTZ,
    source_domain VARCHAR(255),
    title         TEXT,
    description   TEXT,
    url           TEXT        NOT NULL,
    language      VARCHAR(8),
    country_code  VARCHAR(8),
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (article_id)
);
CREATE INDEX IF NOT EXISTS idx_news_published ON raw.news_articles (published_at);
CREATE INDEX IF NOT EXISTS idx_news_source ON raw.news_articles (source_domain);

COMMENT ON TABLE raw.news_articles IS 'Financial / economic news headlines. Source GDELT';
COMMENT ON COLUMN raw.news_articles.article_id IS 'MD5 hash of the URL for idempotent dedumping.';

CREATE TABLE OF NOT EXISTS raw.ingestion_runs (
    run_id        BIGSERIAL   PRIMARY KEY,
    source        VARCHAR(64) NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ,
    rows_inserted INTEGER,
    status        VARCHAR(16) NOT NULL DEFAULT 'running',
    error_message TEXT,
    parameters JSONB
);
CREATE INDEX IF NOT EXISTS idx_runs_source ON raw.ingestion_runs (source, started_at);

COMMENT ON TABLE raw.ingestion_runs IS 'Audit trail for every ingestion job. Useful for monitoring and SLA tracking'