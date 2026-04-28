from __future__ import annotations
from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='env', env_file_encoding='utf-8', extra='ignore', case_sensitive=False)

    observatory_db_url: str = Field(
        default='postgresql+psycopg2://postgres:postgres@localhost:5432/observatory',
        description='SQLAlchemy URL for the application database.'
    )

    fred_api_key: SecretStr = Field(
        default=SecretStr(''),
        description='Free key from https://fred.stlouisfed.org/docs/api/api_key.html'
    )
    gnews_api_key: SecretStr | None = Field(default=None)

    slack_webhook_url: SecretStr | None = Field(default=None)

    default_history_start: str = Field(
        default='2000-01-01',
        description='Earliest date to backfill on first run.'
    )

    @property
    def fred_key(self) -> str:
        key = self.fred_api_key.get_secret_value()

        if not key or key == 'your_fred_api_key_here':
            raise RuntimeError(
                'FRED_API_KEY is not set. Get a free key at '
                'https://fred.stlouisfed.org/docs/api/api_key.html and add it to .env'
            )

        return key

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()