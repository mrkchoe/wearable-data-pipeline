# wearable-data-pipeline

Small, local-first data engineering MVP for wearable CSV data.

## Project question
Are users maintaining consistent daily activity over time, or is engagement degrading?

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
- The dashboard reads from Postgres tables created by dbt models.
- Run the Streamlit app from the repo root:
  `streamlit run dashboards/app.py`
- Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` if not using defaults.

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
- `user_daily_activity` provides one row per user per day.
- `user_baseline_activity` computes per-user baseline steps over first 14 active days.
- `user_activity_deviation` compares each day to the per-user baseline.

## Metric definitions
- `baseline_steps`: median steps over a user's first 14 active days.
- `steps_pct_of_baseline`: steps divided by baseline_steps.
- `steps_delta_from_baseline`: steps minus baseline_steps.
- `is_baseline_window`: whether a day is within the baseline window.

## Run dbt (local)
1) From the repo root:
   `cd dbt`
2) Run models:
   `dbt run`
3) Run tests:
   `dbt test`

## End-to-end run (local)
1) Start Postgres: `docker compose up -d`
2) Ingest CSVs: `python ingestion/ingest.py`
3) Build models: `cd dbt && dbt run`
4) Test models: `cd dbt && dbt test`
5) Launch dashboard: `streamlit run dashboards/app.py`
