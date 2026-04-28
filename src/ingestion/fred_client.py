from __future__ import annotations
from pickle import NONE
from typing import Any, ClassVar
import httpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from src.ingestion.base import BaseIngestor
from src.utils.config import get_settings
from src.utils.logging import get_logger
from src.validation.schemas import FredObservationSchema

log = get_logger(__name__)

DEFAULT_SERIES_ID: list[str] = ['UNRATE', 'GDPC1', 'CPIAUCSL', 'DGS10', 'DGS2', 'T10Y2Y', 'FEDFUNDS', 'INDPRO']

class FredClient(BaseIngestor):
    source_name: ClassVar[str] = 'fred'
    table_name: ClassVar[str] = 'fred_observations'
    conflict_columns: ClassVar[list[str]] = ['series_id', 'obs_date']
    validation_schemas = FredObservationSchema

    BASE_URL: ClassVar[str] = 'https://api.stlouisfed.org/fred/series/observations'
    REQUEST_TIMEOUT_SEC: ClassVar[float] = 30.0

    def __init__(self):
        self._api_key = get_settings().fred_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30), retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)), reraise=True)
    def _fetch_series(self, series_id: str, start: str | None) -> pd.DataFrame:
        params: dict[str, Any] = {'series_id': series_id, 'api_key': self._api_key, 'file_type': 'json'}
        if start:
            params['observation_start'] = start

        log.debug(f'GET {self.BASE_URL} series_id={series_id} start={start}')
        with httpx.Client(timeout=self.REQUEST_TIMEOUT_SEC) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        observations = payload.get('observations', [])

        rows = [
            {
                'series_id': series_id,
                'obs_date': obs['date'],
                'value': float(obs['value']) if obs.get('value') not in (None, '.') else None
            }
            for obs in observations
        ]

        df = pd.DataFrame(rows)
        if df.empty:
            log.warning(f'FRED returned 0 observations for {series_id}')
            return df

        df['obs_date'] = pd.to_datetime(df['obs_date'])
        return df

    def fetch(self, series_ids: list[str] | None = None, start: str | None = None, **_: Any) -> pd.DataFrame:
        ids = series_ids or DEFAULT_SERIES_ID
        if start is None:
            start = get_settings().default_history_start

        frames: list[pd.DataFrame] = []
        for sid in ids:
            df = self._fetch_series(sid, start)
            log.info(f'{sid}: {len(df):,} observations')
            if not df.empty:
                frames.append(df)

        if not frames:
            return pd.DataFrame(columns=['series_id', 'obs_date', 'value'])

        result = pd.concat(frames, ignore_index=True)
        result = result.drop_duplicates(subset=self.conflict_columns, keep='last')
        return result