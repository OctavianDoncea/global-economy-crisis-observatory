from __future__ import annotations
import pytest
import responses
from src.ingestion.fred_client import FredClient

@responses.activate
def test_fetch_single_series_returns_dataframe():
    responses.add(
        responses.GET,
        FredClient.BASE_URL,
        json={
            'observations': [
                {'date': '2024-01-01', 'value': '3.5'},
                {'date': '2024-02-01', 'value': '3.7'}
            ]
        },
        status=200
    )

    df = FredClient()._fetch_series('UNRATE', start='2024-01-01')

    assert len(df) == 2
    assert list(df.columns) == ['series_id', 'obs_date', 'value']
    assert df["series_id"].unique().tolist() == ["UNRATE"]
    assert df['value'].tolist() == [3.5, 3.7]

@responses.activate
def test_fetch_series_handles_missing_values_as_none():
    responses.add(
        responses.GET,
        FredClient.BASE_URL,
        json={
            'observations': [
                {'date': '2024-01-01', 'value': '.'},
                {'date': '2024-02-01', 'value': '3.7'}
            ]
        },
        status=200
    )

    df = FredClient()._fetch_series('UNRATE', start=None)

    assert df.iloc[0]['value'] is None or df.iloc[0]['value'] != df.iloc[0]['value']
    assert df.iloc[1]['value'] == 3.7

@responses.activate
def test_fetch_returns_empty_when_api_returns_no_observations():
    responses.add(responses.GET, FredClient.BASE_URL, json={'observations': []}, status=200)

    df = FredClient()._fetch_series('FAKE', start=None)
    assert df.empty

@responses.activate
def test_fetch_multiple_series_concatenates_results():
    responses.add(responses.GET, FredClient.BASE_URL, json={'observations': [{'date': '2024-01-01', 'value': '1.0'}]}, status=200)
    responses.add(responses.GET, FredClient.BASE_URL, json={'observations': [{'date': '2024-01-01', 'value': '2.0'}]}, status=200)

    df = FredClient().fetch(series_ids=['A', 'B'], start='2024-01-01')

    assert len(df) == 2
    assert set(df['series_id']) == {'A', 'B'}

@responses.activate
def test_retry_on_server_error_then_success(mocker):
    responses.add(responses.GET, FredClient.BASE_URL, status=500)
    responses.add(responses.GET, FredClient.BASE_URL, status=500)
    responses.add(responses.GET, FredClient.BASE_URL, json={'observations': [{'date': '2024-01-01', 'value': '1.0'}]}, status=200)

    mocker.patch('tenacity.nap.time.sleep', return_value=None)

    df = FredClient()._fetch_series('UNRATE', start=None)
    assert len(df) == 1
    assert len(responses.calls) == 3

@responses.activate
def test_retry_gives_up_after_three_failures(mocker):
    for _ in range(5):
        responses.add(responses.GET, FredClient.BASE_URL, status=500)
    mocker.patch('tenacity.nap.time.sleep', return_value=None)

    with pytest.raises(Exception):
        FredClient()._fetch_series('UNRATE', start=None)

    assert len(responses.calls) == 3

def test_class_attributes_match_table_schema():
    assert FredClient.source_name == 'fred'
    assert FredClient.table_name == 'fred_observations'
    assert FredClient.schema_name == 'raw'
    assert FredClient.conflict_columns == ['series_id', 'obs_date']
    assert FredClient.validation_schema is not None