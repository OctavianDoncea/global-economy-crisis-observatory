from __future__ import annotations
import os
from datetime import timedelta
from typing import Any
import httpx

def _slack_alert(context: dict[str, Any]):
    webhook = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        return

    ti = context.get('task_instance')
    if ti is None:
        return

    text = (
        ':rotating_light: *Airflow task failed*\n'
        f'DAG: `{ti.dag_id}`\n'
        f'Task: `{ti.task_id}`\n'
        f"Run: `{context.get('run_id')}`\n"
        f'Try: {ti.try_number}\n'
        f'Log URL: {ti.log_url}'
    )
    try:
        httpx.post(webhook, json={'text': text}, timeout=10).raise_for_status()
    except Exception:
        pass

DEFAULT_ARGS: dict[str, Any] = {
    'owner': 'observatory',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=20),
    'on_failure_callback': _slack_alert,
}
