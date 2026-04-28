from __future__ import annotations
from typing import Any, ClassVar
import hhtpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from src.ingestion.base import BaseIngestor
from src.utils.logging import get_logger
from src.validation.schemas import WorldBankIndicatorSchema

log = get_logger(__name__)

DEFAULT_INDICATORS: list[str] = ['NY.GDP.MKTP.CD', 'NY.GDP.MKTP.KD.ZG', 'SL.UEM.TOTL.ZS', 'FP.CPI.TOTL.ZG', 'GC.DOD.TOTL.GD.ZS', 'NE.EXP.GNFS.ZS', 'BN.CAB.XOKA.GD.ZS']

DEFAULT_COUNTRIES: list[str] = [
    'USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'ITA', 'CAN', 'RUS', 'KOR',
    'BRA', 'AUS', 'MEX', 'IDN', 'ESP', 'TUR', 'SAU', 'ARG', 'ZAF', 'IND',
    'ROU', 'POL', 'NLD', 'BEL', 'SWE', 'CHE', 'NOR', 'DNK', 'FIN', 'AUT'
]

class WorldBankClient(BaseIngestor):
    source_name: ClassVar[str] = 'worldbank'
    table_name: ClassVar[str] = 'worldbank_indicators'
    conflict_columns: ClassVar[list[str]] = ['country_iso', 'indicator_code', 'obs_year']
    validation_schema = WorldBankIndicatorSchema

    BASE_URL: ClassVar[str] = 'https://api.worldbank.org/v2'
    REQUEST_TIMEOUT_SEC: ClassVar[float] = 30.0
    PAGE_SIZE: ClassVar[int] = 1000

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30), retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)), reraise=True)
    def _fetch_page(self, countries: str, indicator: str, page: int, date_range: str) -> tuple[list[dict[str, Any]], int]:
        url = f'{self.BASE_URL}/country/{countries}/indicator/{indicator}'
        params = {'format': 'json', 'per_page': self.PAGE_SIZE, 'page': page, 'date': date_range}

        with httpx.Client(timeout=self.REQUEST_TIMEOUT_SEC) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, list) or len(payload) < 2:
            log.warning(f'World Bank returned unexpected shape for {indicator}: {payload!r:.200}')
            return [], 0

        metadata, data = payload[0], payload[1] or []
        total_pages = int(metadata.get('pages', 1))
        return data, total_pages

    def _fetch_indicator(self, countries: list[str], indicator: str, start_year: int, end_year: int) -> pd.DataFrame:
        country_list = ';'.join(countries)
        date_range = f'{start_year}:{end_year}'
        rows: list[dict[str, Any]] = []

        page = 1
        while True:
            page_rows, total_pages = self._fetch_page(country_list, indicator, page, date_range)
            for r in page_rows:
                country = r.get('countryiso3code') or ''

                if len(country) != 3:
                    continue

                year = r.get('date')
                value = r.get('value')
                rows.append({
                    'country_iso': country,
                    'indicator_code': indicator,
                    'obs_year': int(year) if year else None,
                    'value': float(value) if value is not None else None
                })

            if page >= total_pages:
                break
            page += 1

        df = pd.DataFrame(rows)
        if df.empty:
            log.warning(f'World Bank returned 0 rows for {indicator}')
        else:
            df = df.dropna(subset=['obs_year'])
            df['obs_year'] = df['obs_year'].astype(int)
        
        return df

    def fetch(self, countries: list[str] | None = None, indicators: list[str] | None = None, start_year: int = 1990, end_year: int | None = None, **_: Any) -> pd.DataFrame:
        countries = countries or DEFAULT_COUNTRIES
        indicators = indicators or DEFAULT_INDICATORS
        end_year = end_year or pd.Timestamp.utcnow().year

        frames: list[pd.DataFrame] = []
        for ind in indicators:
            df = self._fetch_indicator(countries, ind, start_year, end_year)
            log.info(f'{ind}: {len(df):,} rows across {df['country_iso'].nunique() if not df.empty() else 0} countries')

            if not df.empty:
                frames.append(df)

        if not frames:
            return pd.DataFrame(columns=['country_iso', 'indicator_code', 'obs_year', 'value'])

        result = pd.concat(frames, ignore_index=True)
        result = result.drop_duplicates(subset=self.conflict_columns, keep='last')

        return result