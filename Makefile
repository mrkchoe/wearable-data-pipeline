# Common local commands for the wearable data pipeline.

.PHONY: help up down logs venv install dbt-deps dbt-run dbt-test

help:
	@echo "Targets:"
	@echo "  up        Start Postgres via Docker"
	@echo "  down      Stop Postgres"
	@echo "  logs      Tail Postgres logs"
	@echo "  venv      Create local Python venv"
	@echo "  install   Install Python dependencies"
	@echo "  dbt-deps  Install dbt packages"
	@echo "  dbt-run   Run dbt models"
	@echo "  dbt-test  Run dbt tests"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postgres

venv:
	python -m venv .venv

install:
	pip install -r requirements.txt

dbt-deps:
	cd dbt && dbt deps

dbt-run:
	cd dbt && dbt run

dbt-test:
	cd dbt && dbt test
