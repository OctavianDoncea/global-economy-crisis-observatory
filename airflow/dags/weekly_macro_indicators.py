from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.dags._common import DEFAULT_ARGS

def _ingest_fred(**context) -> int:
    from src.ingestion.fred_client import FredClient

    # Re-fetch the last 3 years on every run
    start_date = (context['data_interval_end'].replace(year=context['data_interval_end'].year - 3).strftime('%Y-%m-%d'))
    return FredClient().run(start=start_date)

def _ingest_worldbank(**context) -> int:
    from src.ingestion.worldbank_client import WorldBankClient

    end_year = context['data_interval_end'].year
    return WorldBankClient().run(start_year=end_year - 5, end_year=end_year)

with DAG(
    dag_id="weekly_macro_indicators",
    description='Refresh FRED and World Bank macroeconomic indicators',
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="0 8 * * 0",
    catchup=False,
    max_active_runs=1,
    tags=['ingestion', 'macro', 'weekly']
) as dag:
    fred_task = PythonOperator(task_id='ingest_fred', python_callable=_ingest_fred)
    worldbank_task = PythonOperator(task_id='ingest_worldbank', python_callable=_ingest_worldbank)

    # Can run in parallel
    [fred_task, worldbank_task]