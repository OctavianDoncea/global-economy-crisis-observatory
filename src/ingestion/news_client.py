from __future__ import annotations
import hashlib
from typing import Any, ClassVar
import pandas as pd
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from src.ingestion.base import BaseIngestor
from src.utils.logging import get_logger
from src.validation.schemas import NewsArticleSchema

log = get_logger(__name__)

DEFAULT_QUERY: str = (
    '(economy OR recession OR inflation OR "central bank" OR '
    '"interest rate" OR "yield curve" OR "financial crisis")'
)

class GdeltClient(BaseIngestor):
    source_name: ClassVar[str] = 'gdelt'
    table_name: ClassVar[str] = 'news_articles'
    conflict_columns: ClassVar[list[str]] = ['article_id']
    validation_schema = NewsArticleSchema

    BASE_URL: ClassVar[str] = 'https://api.gdeltproject.org/v2/doc/doc'
    REQUEST_TIMEOUT_SEC: ClassVar[float] = 30.0
    MAX_RECORDS: ClassVar[int] = 250

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30), retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)), reraise=True)
    def _call_api(self, params: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.REQUEST_TIMEOUT_SEC) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            text = response.text
        
        try:
            import json
            return json.loads(text)
        except ValueError:
            log.warning('GDELT returned non-JSON response - likely no results.')
            return {'articles': []}

    @staticmethod
    def _hash_url(url: str) -> str:
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def fetch(self, query: str | None = None, hours: int | None = None, max_records: int | None = None, **_: Any) -> pd.DataFrame:
        params = {
            'query': query or DEFAULT_QUERY,
            'mode': 'ArtList',
            'format': 'json',
            'maxrecords': min(max_records or self.MAX_RECORDS, self.MAX_RECORDS),
            'timespan': f'{hours}h',
            'sort': 'DataDesc'
        }

        log.debug(f'GDELT query: {params['query']!r}, timespan={params['timespan']}')
        payload = self._call_api(params)

        articles = payload.get('articles', []) or []
        rows: list[dict[str, Any]] = []
        for art in articles:
            url = art.get('url')
            if not url:
                continue
            
            published = pd.to_datetime(art.get('seendate'), format='%Y%m%dT%H%M%SZ', errors='coerce', utc=True)
            rows.append({
                'article_id': self._hash_url(url),
                'published_at': published,
                'source_domain': art.get('domain'),
                'title': art.get('title'),
                'description': '',
                'url': url,
                'language': art.get('language'),
                'country_code': art.get('sourcecountry'),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            log.warning('GDELT returned 0 articles for the query.')
            return pd.DataFrame(columns=['article_id', 'published_at', 'source_domain', 'title', 'description', 'url', 'language', 'country_code'])

        df = df.drop_duplicates(subset=self.conflict_columns, keep='first')
        if pd.api.types.is_datetime64tz_dtype(df['published_at']):
            df['published_at'] = df['published_at'].dt.tz_convert('UTC').dt.tz_localize(None)

        return df