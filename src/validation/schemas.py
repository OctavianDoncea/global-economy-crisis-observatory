from __future__ import annotations
import pandera.pandas as pa
from pandera.typing import Series

_MIN_DATE = '1900-01-01'

class FredObservationSchema(pa.DataFrameModel):
    series_id: Series[str] = pa.Field(nullable=False, str_length={'min_value': 1})
    obs_date: Series[pa.DateTime] = pa.Field(nullable=False, ge=_MIN_DATE)
    value: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = True
        coerce = True

class WorldBankIndicatorSchema(pa.DataFrameModel):
    country_iso: Series[str] = pa.Field(nullable=False, str_length={'min_value': 2, 'max_value': 3})
    indicator_code: Series[str] = pa.Field(nullable=False, str_length={'min_value': 1})
    obs_year: Series[int] = pa.Field(nullable=False, ge=1900, le=2100)
    value: Series[float] = pa.Field(nullable=False)

    class Config:
        strict = True
        coerce = True

class MarketPriceSchema(pa.DataFrameModel):
    ticker: Series[str] = pa.Field(nullable=False, str_length={'min_value': 1, 'max_value': 16})
    obs_date: Series[pa.DateTime] = pa.Field(nullable=False, ge=_MIN_DATE)
    open: Series[float] = pa.Field(nullable=True, ge=0)
    high: Series[float] = pa.Field(nullable=True, ge=0)
    low: Series[float] = pa.Field(nullable=True, ge=0)
    close: Series[float] = pa.Field(nullable=True, ge=0)
    adj_close: Series[float] = pa.Field(nullable=True, ge=0)
    volume: Series[int] = pa.Field(nullable=True, ge=0)

    class Config:
        strict = True
        coerce = True

class NewsArticleSchema(pa.DataFrameModel):
    article_id: Series[str] = pa.Field(nullable=False, str_length={'min_value': 8, 'max_value': 64})
    published_at: Series[pa.DateTime] = pa.Field(nullable=False)
    source_domain: Series[int] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    url: Series[str] = pa.Field(nullable=False, str_length={'min_value': 1})
    language: Series[str] = pa.Field(nullable=True)
    country_code: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = True
        coerce = True