# wearable-data-pipeline

Local-first data pipeline for wearable CSVs that answers:
Are users maintaining consistent daily activity over time, or is engagement degrading?

## What it does
- Ingests wearable CSVs into Postgres
- Builds dbt models for per-user baselines and deviations
- Serves a Streamlit dashboard with cohort trends

## Quick start
1) Start Postgres:
   `docker compose up -d`
2) Install dependencies:
   `python -m venv .venv && source .venv/bin/activate`
   `pip install -r requirements.txt`
3) Configure dbt profile:
   - Copy `dbt/profiles.yml` to `~/.dbt/profiles.yml`
4) Ingest data:
   `python ingestion/ingest.py`
5) Build + test models:
   `cd dbt && dbt run && dbt test`
6) Run dashboard:
   `streamlit run dashboards/app.py`

## Data expectations
- CSVs in `data/` with names containing `daily` + `activity` load to `raw.daily_activity`
- CSVs with `sleep` in the name load to `raw.sleep`
- Required activity columns: `Id`, `ActivityDate`, `TotalSteps`, `Calories`
- Sleep data is optional; if present it should include `Id`, `SleepDay`, `TotalMinutesAsleep`

## Metrics
- `baseline_steps`: median steps over a user's first 14 active days
- `steps_pct_of_baseline`: steps divided by baseline_steps
- `steps_delta_from_baseline`: steps minus baseline_steps
- `is_baseline_window`: whether a day is within the baseline window

## Models
- `user_daily_activity`
- `user_baseline_activity`
- `user_activity_deviation`
