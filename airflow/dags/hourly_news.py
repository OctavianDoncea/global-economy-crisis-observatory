from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.dags._common import DEFAULT_ARGS

def _ingest_news(**_) -> int:
    from src.ingestion.news_client import GdeltClient

    return GdeltClient().run(hours=2, max_records=250)

with DAG(
    dag_id="hourly_news",
    description = 'Pull rcent macroeconomic news headlines frm GDELT.',
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule='@hourly',
    catchup=False,
    max_active_runs=1,
    tags=['ingestion', 'news', 'hourly']
) as dag:
    PythonOperator(task_id='ingest_gdelt_news', python_callable=_ingest_news)