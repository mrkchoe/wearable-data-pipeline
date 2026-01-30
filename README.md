# wearable-data-pipeline

Small, local-first data engineering MVP for wearable CSV data.

## Project question
Are users maintaining consistent daily activity over time, or is engagement degrading?

## What this repo is
- Ingests external CSV drops into Postgres using Python.
- Transforms and tests data with dbt.
- Orchestrates via GitHub Actions for CI checks.

## Features
- **Raw landing zone**: `data_lake/` is the canonical directory for raw CSV drops.
- **Idempotent ingestion**: Optional `--use-manifest` uses `ops.raw_ingest_manifest` (checksum) to skip unchanged files.
- **Run tracking**: `ops.pipeline_runs` records each run; the pipeline runner logs structured JSON (run_id, step, status, duration_ms) and prints a compact error report on failure.
- **Cloud Postgres**: Set `DATABASE_URL` or `DB_HOST` / `DB_USER` / `DB_PASSWORD` etc. to run against a managed DB (RDS, Cloud SQL, etc.); dbt profile uses the same env vars.
- **Scheduled run**: `.github/workflows/scheduled.yml` runs the pipeline daily (cron) or on demand; set repo secrets for DB.
- **Storage abstraction**: `ingestion/storage.py` — LocalStorage (implemented), S3/GCS stubs for future object storage.
- **Container**: `Dockerfile` runs the pipeline with `python -m ingestion.runner`; set env for DB and optional `PIPELINE_DATA_DIR`.
- **Docs**: Design decisions in `docs/design-decisions.md`; deployment and cloud in `docs/deploy.md`.

## How to run locally
1) Start Postgres:
   `docker compose up -d`
   - Or use `make up` if you prefer.

2) Create a virtualenv and install deps:
   `python -m venv .venv && source .venv/bin/activate` (or `.\\.venv\\Scripts\\activate` on Windows)
   `pip install -r requirements.txt`
   - Or use `make venv` and `make install`.

**Running in WSL**: Use the Linux-style commands above. `make` works; paths are Unix (`/home/...`). Use `source .venv/bin/activate` and `./scripts/test-linux.sh` for tests. If Docker is installed (Docker Desktop with WSL2 backend or Docker in WSL), `docker compose up -d` runs Postgres; then `python -m ingestion.ingest --data-dir sample_data`, `make run-prod`, or `pytest tests/ -v` as needed.

3) Configure dbt profile:
   - Copy `dbt/profiles.yml` to `~/.dbt/profiles.yml`
   - Adjust credentials if needed.

4) Ingest and build:
   - Put CSVs in `data/` or use `sample_data/` for CI-style runs.
   - Run: `python -m ingestion.ingest --data-dir data` (or `--data-dir sample_data`).
   - Run: `cd dbt && dbt run && dbt test`.

## Local dashboard
- The dashboard reads from Postgres tables created by dbt models.
- Run the Streamlit app from the repo root:
  `streamlit run dashboards/app.py`
- Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` if not using defaults.

## Makefile helpers
- `make help` lists available commands.

## Ingest data (local)
- Place CSV drops in `data/` (gitignored) or `data_lake/`.
- Filenames containing `daily` + `activity` load to `raw.daily_activity`; filenames containing `sleep` load to `raw.sleep`.
- Run: `python -m ingestion.ingest --data-dir data` (or `--data-dir data_lake`)
- For idempotent runs (skip unchanged files): add `--use-manifest`

## Run pipeline with run tracking
- Put CSVs in `data_lake/` (or use `sample_data/`).
- Run: `PIPELINE_DATA_DIR=data_lake PIPELINE_USE_MANIFEST=1 python -m ingestion.runner` (or `make run-prod`)
- Runs ingest (with manifest) then dbt, logs JSON to stdout, and writes to `ops.pipeline_runs`. On failure prints a compact error report and exits non-zero.

## Run tests
- Unit and integration tests (integration requires Postgres, e.g. `docker compose up -d`):
  `pytest tests/ -v`
- From repo root; set `DB_HOST`, `DB_PORT`, etc. if Postgres is not on localhost.
- **Test on Linux**: CI runs on `ubuntu-latest` (ingest + pytest + dbt) on every push/PR. To run the same locally:
  - **Push to GitHub** and check the Actions tab — tests run on Ubuntu automatically.
  - **WSL or Linux**: Start Postgres (`docker compose up -d`), then `./scripts/test-linux.sh`.
  - **Docker on Linux**: `docker compose up -d` then `docker run --rm -v "$(pwd):/app" -w /app --network host -e DB_HOST=127.0.0.1 python:3.11-slim bash /app/scripts/test-linux.sh`.
  - **Docker on Windows**: Start Postgres with `docker compose up -d`, then run the test script in a container with `DB_HOST=host.docker.internal` (e.g. `docker run --rm -v "%cd%:/app" -w /app -e DB_HOST=host.docker.internal -e DB_PORT=5432 -e DB_NAME=wearable -e DB_USER=wearable -e DB_PASSWORD=wearable python:3.11-slim bash /app/scripts/test-linux.sh`).

## Windows / PowerShell (no Make)
- **Tests**: `pytest tests/ -v`
- **Env vars** (one line): `$env:DB_HOST="localhost"; $env:DB_PORT="5432"; $env:DB_NAME="wearable"; $env:DB_USER="wearable"; $env:DB_PASSWORD="wearable"`
- **Run pipeline with tracking**: `$env:PIPELINE_DATA_DIR="data_lake"; $env:PIPELINE_USE_MANIFEST="1"; python -m ingestion.runner`
- **Ingest only**: `python -m ingestion.ingest --data-dir sample_data` (or `data_lake` with `--use-manifest`)
- Start Postgres first: `docker compose up -d`. If Postgres is not running, ingest and runner print a short error and exit.

## Cloud and deployment
- **Cloud Postgres**: Set `DATABASE_URL` or `DB_*`; same code works locally or against RDS/Cloud SQL.
- **Scheduled workflow**: Add repo secrets (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT` or `DATABASE_URL`); the **scheduled** workflow runs ingest + dbt on a cron (e.g. daily 06:00 UTC).
- **Docker**: `docker build -t wearable-pipeline .` then run with `-e DATABASE_URL=...` or `-e DB_HOST=...` etc. See `docs/deploy.md` for scheduled jobs (Cloud Run Jobs, ECS, etc.).

## Folder layout
- `ingestion/` Python ingestion, pipeline runner, DB and storage helpers.
- `dbt/` dbt project and models.
- `data/` Local CSV drops (ignored by git).
- `data_lake/` Canonical raw landing zone (contents ignored by git).
- `docs/` Design decisions and deployment (`deploy.md`).

## dbt model layers
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
2) Ingest CSVs: `python -m ingestion.ingest --data-dir data` (or `--data-dir sample_data`)
3) Build models: `cd dbt && dbt run`
4) Test models: `cd dbt && dbt test`
5) Launch dashboard: `streamlit run dashboards/app.py`
