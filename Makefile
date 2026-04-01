# Wearable data pipeline — common local commands.
# Full stack: Postgres (warehouse), MinIO (S3-compatible), Airflow.

COMPOSE := docker compose -f docker/docker-compose.yml

.PHONY: help up up-all down logs logs-airflow ps minio-ui venv install \
	dbt-deps dbt-run dbt-test test detect upload load smoke airflow-build run-prod

help:
	@echo "Targets:"
	@echo "  up          Start Postgres + MinIO (+ init job) — no Airflow"
	@echo "  up-all      Start warehouse, MinIO, Airflow (web on :8080, admin/admin)"
	@echo "  down        Stop docker compose stack"
	@echo "  ps          docker compose ps"
	@echo "  logs        Tail Postgres logs"
	@echo "  logs-airflow Tail Airflow web + scheduler"
	@echo "  minio-ui    Print MinIO console URL (http://localhost:9001)"
	@echo "  venv        Create local Python venv"
	@echo "  install     pip install -r requirements.txt"
	@echo "  detect      Detect new/changed CSVs vs manifests (needs Postgres for S3 checks)"
	@echo "  upload      Upload DATA_DROP_DIR CSVs to S3/MinIO (partitioned)"
	@echo "  load        Reload staging schema in Postgres from S3"
	@echo "  smoke       upload + load + dbt run/test (host must reach MinIO + Postgres)"
	@echo "  run-prod    Local ingest + dbt via ingestion.runner (no S3; use after up)"
	@echo "  dbt-deps    dbt deps"
	@echo "  dbt-run / dbt-test"
	@echo "  test        pytest"
	@echo "  airflow-build  Build custom Airflow image only"

up:
	$(COMPOSE) up -d postgres minio minio-init

up-all:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f postgres

logs-airflow:
	$(COMPOSE) logs -f airflow-webserver airflow-scheduler

minio-ui:
	@echo "MinIO console: http://localhost:9001  (minioadmin / minioadmin)"

venv:
	python -m venv .venv

install:
	pip install -r requirements.txt

detect:
	python -m ingestion.detect

upload:
	python -m ingestion.upload_to_s3

load:
	python -m ingestion.load_s3_to_staging

smoke: upload load dbt-run dbt-test

dbt-deps:
	cd dbt && dbt deps

dbt-run:
	cd dbt && dbt run

dbt-test:
	cd dbt && dbt test

test:
	pytest tests/ -v

airflow-build:
	$(COMPOSE) build airflow-webserver

run-prod:
	PIPELINE_DATA_DIR=sample_data PIPELINE_USE_MANIFEST=1 python -m ingestion.runner
