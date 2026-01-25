# wearable-data-pipeline

Small, local-first data engineering MVP for wearable CSV data.

## What this repo is
- Ingests external CSV drops into Postgres using Python.
- Ingests analytics events via a FastAPI service into a raw landing table.
- Transforms and tests data with dbt.
- Orchestrates locally with Prefect.

## What this repo is not (yet)
- No dashboards or frontend.
- No cloud services.
- No sample data checked in.

## Quick start (local)
1) Start Postgres:
   `docker compose up -d`
   - Or use `make up` if you prefer.

2) Create a virtualenv and install deps:
   `python -m venv .venv && source .venv/bin/activate`
   `pip install -r requirements.txt`
   - Or use `make venv` and `make install`.

3) Configure dbt profile:
   - Copy `dbt/profiles.yml` to `~/.dbt/profiles.yml`
   - Adjust credentials if needed.

4) Start ingestion API:
   `make ingest-api`

5) Generate demo events:
   `make generate-events`

6) Run pipeline:
   `make run`

## Makefile helpers
- `make help` lists available commands.

## Ingest data (local)
- Place CSV drops in `data/` (gitignored).
- Filenames containing `daily` + `activity` load to `raw.daily_activity`.
- Filenames containing `sleep` load to `raw.sleep`.
- Run: `python ingestion/ingest.py`

## Architecture (local-first)
```
Event Generator -> FastAPI Ingestion -> Postgres raw.raw_events -> dbt stg_events
                                                |                     |
                                                |                     -> daily_user_summary
CSV ingestion ----------------------------------+--> stg_daily_activity/stg_sleep
                    Orchestrator (Prefect) runs: seed -> dbt run -> dbt test
```

## Folder layout
- `ingestion/` Python ingestion placeholders.
- `dbt/` dbt project and models.
- `data/` Local CSV drops (ignored by git).
- `services/ingestion/` FastAPI ingestion service for event batches.
- `schemas/` JSON Schemas for the event contract.
- `orchestration/` Prefect flow for local runs.
- `scripts/` Demo data generator.

## dbt model layers (MVP)
- `stg_daily_activity` standardizes raw activity columns and types.
- `stg_sleep` standardizes raw sleep columns and types.
- `daily_user_summary` provides a daily user grain by joining activity + sleep.

## Run dbt (local)
1) From the repo root:
   `cd dbt`
2) Run models:
   `dbt run`
3) Run tests:
   `dbt test`

## Tables produced
- `raw.raw_events`: raw event landing table with JSON payloads.
- `stg_events`: parsed event metadata + typed payload fields.
- `stg_daily_activity`, `stg_sleep`: typed CSV staging models.
- `daily_user_summary`: daily user grain mart (activity + sleep).

## Why this is DE-grade
- Strong contracts: JSON Schema validation at ingestion.
- Idempotency: dedupe on `event_id`.
- Reliability: raw landing table before transformations.
- Orchestration: Prefect flow wires seed + dbt run + dbt test.
- Observability: structured logs + basic counters (received/rejected/deduped).
