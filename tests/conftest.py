from __future__ import annotations
import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture(autouse=True)
def _stub_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    from src.utils import config

    config.get_settings.cache_clear()

    monkeypatch.setenv('FRED_API_KEY', 'test_fred_key')
    monkeypatch.setenv('OBSERVATORY_DB_URL', 'postgresql+psycopg2://test:test@localhost:5432/test')
    monkeypatch.setenv('DEFAULT_HISTORY_START', '2020-01-01')

    yield

    config.get_settings.cache_clear()

@pytest.fixture
def mock_engine() -> Iterator[MagicMock]:
    with patch('src.utils.db.get_engine') as mock:
        engine = MagicMock()
        mock.return_value = engine
        yield engine