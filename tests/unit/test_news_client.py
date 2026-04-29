from __future__ import annotations
import responses
from src.ingestion.news_client import GdeltClient

@responses.activate
def test_fetch_returns_dataframe_with_required_columns():
    responses.add(
        responses.GET,
        GdeltClient.BASE_URL,
        json={
            'articles': [
                {
                    'url': 'https://example.com/a',
                    'title': 'Inflation rises',
                    'seendate': '20240115T143000Z',
                    'domain': 'example.com',
                    'language': 'English',
                    'sourcecountry': 'US'
                }
            ]
        },
        status=200
    )

    df = GdeltClient().fetch(hours=1)

    assert len(df) == 1
    expected = {'article_id', 'published_at', 'source_domain', 'title', 'description', 'url', 'language', 'country_code'}
    assert set(df.columns) >= expected

@responses.activate
def test_url_hashing_is_stable_across_calls():
    responses.add(responses.GET, GdeltClient.BASE_URL, json={'articles': [{'url': 'https://example.com/x', 'seendate': '20240101T000000Z'}]}, status=200)
    responses.add(responses.GET, GdeltClient.BASE_URL, json={"articles": [{"url": "https://example.com/x", "seendate": "20240101T000000Z"}]}, status=200)

    df1 = GdeltClient().fetch(hours=1)
    df2 = GdeltClient().fetch(hours=1)
    assert df1.iloc[0]['article_id'] == df2.iloc[0]['article_id']

@responses.activate
def test_drops_articles_without_url():
    responses.add(
        responses.GET,
        GdeltClient.BASE_URL,
        json={
            'articles': [
                {'url': None, 'title': 'broken', 'seendate': '20240101T000000Z'},
                {'url': 'https://ok.com', 'title': 'ok', 'seendate': '20240101T000000Z'}
            ]
        },
        status=200
    )

    df = GdeltClient().fetch(hours=1)
    assert len(df) == 1
    assert df.iloc[0]['url'] == 'https://ok.com'

@responses.activate
def test_dedupes_within_single_response():
    responses.add(
        responses.GET,
        GdeltClient.BASE_URL,
        json={
            'articles': [
                {'url': 'https://example.com/a', 'seendate': '20240101T000000Z'},
                {'url': 'https://example.com/a', 'seendate': '20240101T000000Z'},
            ]
        },
        status=200
    )

    df = GdeltClient().fetch(hours=1)
    assert len(df) == 1