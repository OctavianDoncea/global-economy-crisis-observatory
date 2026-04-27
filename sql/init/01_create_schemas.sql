CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

COMMENT ON SCHEMA raw IS 'Landing zone for digested data. Append-or-upsert only.';
COMMENT ON SCHEMA stagind IS 'Cleaned and typed source models. Owned by dbt.';
COMMENT ON SCHEMA marts IS 'Business-facing fact and dimension tables. Owned by dbt.';