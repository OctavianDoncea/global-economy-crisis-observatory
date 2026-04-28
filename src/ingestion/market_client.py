from __future__ import annotations
import time
from typing import Any, ClassVar
import pandas as pd
import yfinance as yf
from src.ingestion.base import BaseIngestor
from src.utils.config import get_settings
from src.utils.logging import get_logger
from src.validation.schemas import MarketPriceSchema

log = get_logger(__name__)

DEFAULT_TICKERS: list[str] = ['^GSPC', '^IXIC', '^DJI', '^FTSE', '^GDAXI', '^N225', '^STOXX50E', '^VIX', 'DX-Y.NYB', 'GC=F', 'CL=F', 'BTC-USD']

class MarketClient(BaseIngestor):
    source_name: ClassVar[str] = 'market'
    table_name: ClassVar[str] = 'market_prices'
    conflict_columns: ClassVar[list[str]] = ['ticker', 'obs_date']
    validation_schema = MarketPriceSchema

    SLEEP_BETWEEN_TICKERS_SEC: ClassVar[float] = 0.5

    def _fetch_ticker(self, ticker: str, start: str, end: str | None) -> pd.DataFrame:
        try:
            raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False, threads=False)
        except Exception as e:
            log.error(f'yfinance failed for {ticker}: {e}')
            return pd.DataFrame()

        if raw is None or raw.empty():
            log.warning(f'yfinance returned no data for {ticker}')
            return pd.DataFrame()

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw.reset_index().rename(columns={'Date': 'obs_date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'})
        df['ticker'] = ticker
        df['obs_date'] = pd.to_datetime(df['obs_date']).dt.tz_localize(None)

        return df[['ticker', 'obs_date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]

    def fetch(self, tickers: list[str] | None = None, start: str | None = None, end: str | None = None, **_: Any) -> pd.DataFrame:
        tickers = tickers or DEFAULT_TICKERS
        start = start or get_settings().default_history_start

        frames: list[pd.DataFrame] = []
        for tk in tickers:
            df = self._fetch_ticker(tk, start, end)
            log.info(f'{tk}: {len(df):,} rows')
            if not df.empty:
                frames.append(df)
            time.sleep(self.SLEEP_BETWEEN_TICKERS_SEC)

        if not frames:
            return pd.DataFrame(columns=['ticker', 'obs_date', 'open', 'high', 'low', 'close', 'adj_close', 'volume'])

        result = pd.concat(frames, ignore_index=True)
        result = result.drop_duplicates(subset=self.conflict_columns, keep='last')
        return result