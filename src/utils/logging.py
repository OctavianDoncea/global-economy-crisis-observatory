from __future__ import annotations
import os
import sys
from loguru import logger

logger.remove()

_running_in_airflow = bool(os.environ.get('AIRFLOW_HOME'))

if _running_in_airflow:
    logger.add(
        sys.stdout,
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}',
        backtrace=True,
        diagnose=False
    )
else:
    logger.add(
        sys.stderr,
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format=(
            '<green>{time:HH:mm:ss}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan> | '
            '<level>{message}</level>'
        ),
        backtrace=True,
        diagnose=True,
        colorize=True
    )

def get_logger(name: str | None = None):
    return logger.bind(name=name) if name else logger