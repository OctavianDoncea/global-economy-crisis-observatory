.PHONY: help setup up down restart logs ps clean \
		ingest-fred ingest-worldbank ingest-market ingest-news ingest-all \
		psql airflow-shell test test-cov lint format check init-db

help:
	@echo "Global Economy Crisis Observatory - make targets"
	@echo ""
	@echo "Setup:"
	@echo "	setup		      Create venv and install dependencies"
	@echo "	init-db 	      Initialize the application schemas in PostgreSQL"
	@echo ""
	@echo "Docker:"
	@echo "	up			      Start all services (PostgreSQL + Airflow)"
	@echo "	down              Stop all services"
	@echo " restart           Restart all services"
	@echo " logs              Tail logs from all services"
	@echo " ps                List running services"
	@echo " clean             Stop services and remove volumes (DESTRUCTIVE)"
	@echo ""
	@echo "Ingestion (run locally for testing, Airflow runs them in production):"
	@echo " ingest-fred       Pull FRED macro indicators"
	@echo " ingest-worldbank  Pull World Bank development indicators"
	@echo " ingest-market     Pull yfinance market data"
	@echo " ingest-news       Pull GDELT news headlines"
	@echo " ingest-all        Run all ingestors"
	@echo ""
	@echo "Quality:"
	@echo " test              Run unit tests"
	@echo " test-cov          Run tests with coverage report"
	@echo " lint              Run ruff + black checks (no fixes)"
	@echo " format            Auto-format code"
	@echo " check             Run lint + tests"
	@echo ""
	@echo "Utilities:"
	@echo " psql              Open a psql shell to the observatory database"
	@echo " airflow-shell     Open a bash shell in the Airflow scheduler container"

setup:
	test -f .env || cp .env.example .env
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pre-commit install
	echo ""
	echo "Setup complete. Edit .env to add your FRED_API_KEY, then run 'make up'."

init-db:
	docker compose exec postgres psql -U postgres -d observatory -f docker-entrypoint

up:
	docker compose up -d
	@echo ""
	@echo "Services starting. Check status with 'make ps'."
	@echo "Airflow UI: http://localhost:8080 (admin/admin)"
	@echo "PostgreSQL: localhost:5432 (postgres/postgres)"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v
	@echo "All containers stopped and volumes removed."

ingest-fred:
	.venv/bin/python -m src.cli ingest fred

ingest-worldbank:
	.venv/bin/python -m src.cli ingest worldbank

ingest-market:
	.venv/bin/python -m src.cli ingest market

ingest-news:
	.venv/bin/python -m src.cli ingest news

ingest-all:
	.venv/bin/python -m src.cli ingest all

test:
	.venv/bin/pytest test/unit -v

test-cov:
	.venv/bin/pytest test/unit -v --cov=src --cov-report=term-missing --cov-report=html

lint:
	.venv/bin/ruff check src tests
	.venv/bin/black --check src tests

format:
	.venv/bin/ruff/check --fix src tests
	.venv/bin/black src tests

check: lint test

psql:
	docekr compose exec postgres psql -U postgres -d observatory

airflow-shell:
	docker compose exec airflow-scheduler bash