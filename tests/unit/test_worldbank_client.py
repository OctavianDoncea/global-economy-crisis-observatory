from __future__ import annotations
import email
import re
import responses
from src.ingestion.worldbank_client import WorldBankClient

API_RE = re.compile(r'^https://api\.worldbank\.org/v2/country/.+/indicator/.+$')

@responses.activate
def fetch_test_indicator_paginates_correctly():
    page_1 = [
        {'pages': 2, 'per_page': 1000, 'page': 1, 'total': 2},
        [
            {
                'countryiso3code': 'USA',
                'date': 2020,
                'value': 21000.0
            }
        ]
    ]
    page_2 = [
        {'pages': 2, 'per_page': 1000, 'page': 2, 'total': 2},
        [
            {
                'countryiso3code': 'DEU',
                'date': 2020,
                'value': 4000.0
            }
        ]
    ]
    responses.add(responses.GET, API_RE, json=page_1, status=200)
    responses.add(responses.GET, API_RE, json=page_2, status=200)

    df = WorldBankClient()._fetch_indicator(countries=['USA', 'DEU'], indicator='NY.GDP.MKTP.CD', start_year=2020, end_year=2020)

    assert len(df) == 2
    assert set(df['country_iso']) == {'USA', 'DEU'}
    assert len(responses.calls) == 2

@responses.activate
def test_fetch_indicator_skips_aggregate_country_codes():
    payload = [
        {'pages': 1, 'per_page': 1000, 'page': 1, 'total': 2},
        [
            {'countryiso3code': 'USA', 'date': '2020', 'value': 21000.0},
            {'countryiso3code': 'EUU', 'date': '2020', 'value': 16000.0},
            {'countryiso3code': '', 'date': '2020', 'value': 100.0}
        ]
    ]
    responses.add(responses.GET, API_RE, json=payload, status=200)

    df = WorldBankClient()._fetch_indicator(countries=['USA'], indicator='NY.GSP.MKTP.CD', start_year=2020, end_year=2020)

    assert len(df) == 2
    assert set(df['country_iso']) == {'USA', "EUU"}

@responses.activate
def fetch_test_indicator_handles_empty_responses():
    responses.add(responses.GET, API_RE, json=[{'message': [{'id': '120', 'key': 'Invalid', 'value': 'no data'}]}], status=200)

    df = WorldBankClient()._fetch_indicator(countries=['XYZ'], indicator='FAKE', start_year=2020, end_year=2020)
    assert df.empty

@responses.activate
def test_fetch_drops_null_year_rows():
    payload = [
        {'pages': 1, 'per_page': 1000, 'page': 1, 'total': 1},
        [
            {'countryiso3code': 'USA', 'date': None, 'value': 1.0},
            {'countryiso3code': 'USA', 'date': 2020, 'value': 2.0},
        ]
    ]
    responses.add(responses.GET, API_RE, json=payload, status=200)

    df = WorldBankClient(). _fetch_indicator(countries=['USA'], indicator='X', start_year=2020, end_year=2020)

    assert len(df) == 1
    assert df.iloc[0]['obs_year'] == 2020

def test_class_attributes():
    assert WorldBankClient.source_name == 'worldbank'
    assert WorldBankClient.table_name == 'worldbank_indicators'
    assert WorldBankClient.conflict_columns == ['country_iso', 'indicator_code', 'obs_year']