from __future__ import annotations
import pandas as pd
import pandera.errors
import pytest
from src.validation.schemas import FredObservationSchema, MarketPriceSchema, WorldBankIndicatorSchema, NewsArticleSchema

def test_fred_schema_accepts_valid_data():
    df = pd.DataFrame({
        'series_id': ['UNRATE', 'GDPC1'],
        'obs_date': pd.to_datetime(['20204-01-01', '2024-01-01']),
        'value': [3.5, 22000.0]
    })
    out = FredObservationSchema.validate(df)
    assert len(out) == 2

def test_fred_schema_allows_null_value():
    df = pd.DataFrame({
        'series_id': ['UNRATE'],
        'obs_date': pd.to_datetime(['20204-01-01']),
        'value': None
    })
    FredObservationSchema.validate(df)

def test_fred_schema_rejects_missing_series_id():
    df = pd.DataFrame({
        'series_id': [None],
        'obs_date': pd.to_datetime(['2024-01-01']),
        'value': 3.5
    })
    with pytest.raises(pandera.errors.SchemaErrors):
        FredObservationSchema.validate(df, lazy=True)

def test_worldbank_schema_year_range():
    df = pd.DataFrame({
        'country_iso': ['USA'],
        'indicator_code': ['NY.GDP.MKTP.CD'],
        'obs_year': [1850],
        'value': [1.0]
    })
    with pytest.raises(pandera.errors.SchemaErrors):
        WorldBankIndicatorSchema.validate(df, lazy=True)

def test_market_schema_rejects_negative_prices():
    df = pd.DataFrame({
        'ticker': ['X'],
        'obs_date': pd.to_datetime(['2024-01-01']),
        'open': [10.0],
        'high': [11.0],
        'low': [9.0],
        'close': [-1.0],
        'adj_close': [10.5],
        'volume': [1000]
    })
    with pytest.raises(pandera.errors.SchemaErrors):
        MarketPriceSchema.validate(df, lazy=True)

def test_news_schema_requires_url():
    df = pd.DataFrame({
        'article_id': ['a' * 32],
        'published_at': pd.to_datetime(['2024-01-01']),
        'source_domain': ['x.com'],
        'title': ['t'],
        'description': [''],
        'url': [''],
        'language': ['en'],
        'country_code': ['US']
    })
    with pytest.raises(pandera.errors.SchemaErrors):
        NewsArticleSchema.validate(df, lazy=True)