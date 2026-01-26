# wearable-data-pipeline

Small, local-first data engineering MVP for wearable CSV data.

## What this repo is
- Ingests external CSV drops into Postgres using Python.
- Transforms and tests data with dbt.
- Orchestrates via GitHub Actions for CI checks.

## What this repo is not (yet)
- No cloud services.
- No production deployment.

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

## Local dashboard
- Sample data lives at `sample_data/daily_user_summary_sample.csv`.
- Run the Streamlit app from the repo root:
  `streamlit run dashboards/app.py`
- Use the sidebar to point to a different local CSV if needed.

## Makefile helpers
- `make help` lists available commands.

## Ingest data (local)
- Place CSV drops in `data/` (gitignored).
- Filenames containing `daily` + `activity` load to `raw.daily_activity`.
- Filenames containing `sleep` load to `raw.sleep`.
- Run: `python ingestion/ingest.py`

## Folder layout
- `ingestion/` Python ingestion placeholders.
- `dbt/` dbt project and models.
- `data/` Local CSV drops (ignored by git).

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
