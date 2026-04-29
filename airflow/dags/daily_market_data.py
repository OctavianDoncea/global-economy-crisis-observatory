from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.dags._common import DEFAULT_ARGS

def _run_market_ingestion(**context) -> int:
    """Pull a rolling window of recent prices"""
    from src.ingestion.market_client import MarketClient

    # Look back 7 days to catch any late corrections from the source
    end_date = context['data_interval_end'].strftime('%Y-%m-%d')
    start_date = (context['data_interval_end'] - timedelta(days=7)).strftime('%Y-%m-%d')

    client = MarketClient()
    return client.run(start=start_date, end=end_date)

with DAG(
    dag_id="daily_market_data",
    description="Pull daily OHLCV for indices, FX, commodities, and crypto.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="0 6 * * 1-5",
    catchup=False,
    max_active_runs=1,
    tags=["ingestion", "market", "daily"],
) as dag:
    PythonOperator(task_id='ingest_market_prices', python_callable=_run_market_ingestion)