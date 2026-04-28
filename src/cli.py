from __future__ import annotations
import sys
import click
from src.ingestion.fred_client import FredClient
from src.ingestion.market_client import MarketClient
from src.ingestion.news_client import GdeltClient
from src.ingestion.worldbank_client import WorldBankClient
from src.utils.logging import get_logger

log = get_logger(__name__)

@click.group()
def cli():
    """Global Economy Crisis Observatory - operational CLI"""

@cli.group()
def ingest():
    """Run an ingestion job."""

@ingest.command('fred')
@click.option('--series', '-s', multiple=True, help='Override default series IDs.')
@click.option('--start', default=None, help='Earliest observation date (YYYY-MM-DD).')
def ingest_fred(series: tuple[str, ...], start: str | None) -> None:
    client = FredClient()
    n = client.run(series_ids=list(series) or None, start=start)
    click.echo(f'FRED ingestion complete: {n:,} rows')

@ingest.command('worldbank')
@click.option('--country', '-c', multiple=True, help='ISO-3 country codes.')
@click.option('--indicator', '-i', multiple=True, help='World Bank indicator codes.')
@click.option('--start-year', type=int, default=1990)
@click.option('--end-year', type=int, default=None)
def ingest_worldbank(country: tuple[str, ...], indicator: tuple[str, ...], start_year: int, end_year: int | None):
    client = WorldBankClient()
    n = client.run(countries=list(country) or None, indicators=list(indicator) or None, start_year=start_year, end_year=end_year)
    click.echo(f'World Bank ingestion complete {n:,} rows.')

@ingest.command('market')
@click.option('--ticker', '-t', multiple=True, help='Override default tickers.')
@click.option('--start', default=None, help='Earliest date (YYYY-MM-DD).')
@click.option('--end', default=None, help='Latest date (YYYY-MM-DD).')
def ingest_market(ticker: tuple[str, ...], start: str | None, end: str | None):
    client = MarketClient()
    n = client.run(tickers=list(ticker) or None, start=start, end=end)
    click.echo(f'Market ingestion complete: {n:,} rows.')

@ingest.command('news')
@click.option('--query', '-q', default=None, help='GDELT search query.')
@click.option('--hours', '-H', type=int, default=None, help='Look-back window in hours.')
@click.option('--max-records', '-n', type=int, default=250)
def ingest_news(query: str | None, hours: int, max_records: int):
    client = GdeltClient()
    n = client.run(query=query, hours=hours, max_records=max_records)
    click.echo(f'News ingestion complete: {n:,} rows.')

@ingest.command('all')
def ingest_all():
    failures: list[str] = []

    for client_cls in (FredClient, WorldBankClient, MarketClient, GdeltClient):
        name = client_cls.source_name
        click.echo(f'\n{name.upper()}')

        try:
            client_cls().run()
        except Exception as e:
            log.exception(f'{name} ingestion failed')
            failures.append(f'{name}: {e}')

    if failures:
        click.echo('\n Some inhestors failed:')
        for f in failures:
            click.echo(f'{f}')
        sys.exit(1)
    else:
        click.echo('\nAll ingestors completed successfully.')

if __name__ == '__main__':
    cli()