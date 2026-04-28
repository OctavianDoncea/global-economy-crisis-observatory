from __future__ import annotations
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection
from src.utils.config import get_settings
from src.utils.logging import get_logger

log = get_logger(__name__)

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine

    if _engine is None:
        url = get_settings().observatory_db_url
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
        log.debug(f"Database engine created for {url.split('@')[-1]}")
    
    return _engine

def upsert_df(df: pd.DataFrame, *, table: str, schema: str = 'raw', conflict_columns: list[str], chunk_size: int = 1000) -> int:
    if df.empty:
        log.info(f'upsert_df: empty DataFrame, skipping {schema}.{table}')
        return 0

    engine = get_engine()

    from sqlalchemy import MetaData, Table

    md = MetaData(schema=schema)
    target = Table(table, md, autoload_with=engine)

    update_cols = [c.name for c in target.columns if c.name not in conflict_columns]
    total = 0
    records = df.to_dict(orient='records')

    with engine.begin() as conn:
        for start in range(0, len(records), chunk_size):
            chunk = records[start : start + chunk_size]
            stmt = pg_insert(target).values(chunk)
            stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_={c: stmt.excluded[c] for c in update_cols})
            conn.execute(stmt)
            total += len(chunk)

    log.info(f'upsert_df: {total} rows submitted to {schema}.{table}')
    return total

@contextmanager
def run_log(source: str, parameters: dict[str, Any] | None = None) -> Iterator[int]:
    """Context manager that records ingestion runs in `raw.ingestion_runs`."""
    engine = get_engine()
    started = datetime.now(UTC)
    parameters_json = json.dumps(parameters or {}, default=str)

    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO raw.ingestion_runs (source, started_at, parameters)
                VALUES (:source, :started, 'running', CAST(:params AS JSONB))
                RETURNING run_id
                """
            ),
            {'source': source, 'started': started, 'params': parameters_json}
        )
        run_id = int(result.scalar_one())

    log.info(f'Started ingestion run #{run_id} for source={source}')

    try:
        yield run_id
    except Exception as e:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE raw.ingestion_runs
                        SET finished_at = NOW(),
                            status = 'failed',
                            error_message = :err
                    WHERE run_id = :rid
                    """
                ),
                {'err': str(e)[:1000], 'rid': run_id}
            )
        log.error(f'Ingestion run #{run_id} failed: {e}')
        raise
    else:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE raw.ingestion_runs
                        SET finished_at = NOW(), status = 'success'
                    WHERE run_id = :rid
                    """
                ),
                {'rid': run_id}
            )
        log.info(f'Completed ingestion run #{run_id} for source={source}')

def update_run_rows(run_id: int, rows_inserted: int):
    with get_engine().begin() as conn:
        conn.execute(
            text(
                'UPDATE raw.ingestion_runs SET rows_inserted = :n WHERE run_id = :rid'
            ),
            {'n': rows_inserted, 'rid': run_id}
        )

@contextmanager
def get_connection() -> Iterator[Connection]:
    with get_engine().begin() as conn:
        yield conn