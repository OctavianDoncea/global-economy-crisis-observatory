from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, ClassVar
import pandas as pd
from pandera.api.pandas.model import DataFrameModel
from src.utils.db import run_log, update_run_rows, upsert_df
from src.utils.logging import get_logger

log = get_logger(__name__)

class BaseIngestor(ABC):
    source_names: ClassVar[str]
    table_name: ClassVar[str]
    schema_name: ClassVar[str] = 'raw'
    conflict_columns: ClassVar[list[str]]
    validation_schema: ClassVar[type[DataFrameModel] | None] = None

    @abstractmethod
    def fetch(self, **kwargs: Any) -> pd.DataFrame:
        """Return a DataFrame matching the taw table's columns (minus `fetched_at`,
        which is added by the database default). Should be implemented by subclasses."""

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.validation_schema is None or df.empty:
            return df
        
        return self.validation_schema.validate(df, lazy=True)

    def load(self, df: pd.DataFrame) -> int:
        return upsert_df(df, table=self.table_name, schema=self.schema_name, conflict_columns=self.conflict_columns)

    def run(self, **kwargs: Any) -> int:
        log.info(f'[{self.source_name}] starting ingestion with kwargs={kwargs}')

        with run_log(self.source_name, parameters=kwargs) as run_id:
            df = self.fetch(**kwargs)
            log.info(f'[{self.source_name}] fetched {len(df):,} rows')

            df = self.validate(df)
            log.info(f'[{self.source_name}] validation passed')

            n = self.load(df)
            update_run_rows(run_id, n)
            log.info(f'[{self.source_name}] loaded {n:,} rows into '
                     f'{self.schema_name}.{self.table_name}')
            
            return n