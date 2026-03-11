# Wearable Data Pipeline

End-to-end local-first data pipeline for ingesting wearable device CSV data, transforming it with dbt, and analyzing user engagement trends through a lightweight dashboard.

The project answers a simple behavioral analytics question:

**Are users maintaining consistent daily activity over time, or is engagement degrading?**

---

## Architecture

CSV drops → Python ingestion → Postgres warehouse → dbt models/tests → Streamlit dashboard

This repository demonstrates a realistic analytics workflow:

- Batch ingestion of raw wearable device data
- Relational storage in Postgres
- Data transformation and testing with dbt
- Analytical metrics for user engagement trends
- Lightweight visualization through Streamlit

---

## What it does

- Ingests wearable CSVs into **Postgres raw tables**
- Builds **dbt models** for per-user baselines and deviations
- Serves a **Streamlit dashboard** for cohort-level engagement trends

<img width="1169" height="613" alt="Screenshot 2026-02-17 at 3 35 33 PM" src="https://github.com/user-attachments/assets/7de6548a-c97c-422c-ae3c-0c7ddfbe6b64" />

---

## Quick start

Start the database:
docker compose up -d

Install dependencies:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Configure dbt profile:
cp dbt/profiles.yml ~/.dbt/profiles.yml

Ingest raw data:
python ingestion/ingest.py

Build and test transformation models:
cd dbt
dbt run
dbt test

Run the dashboard:
streamlit run dashboards/app.py


---

## Data expectations

CSV files should be placed in the `data/` directory.

Activity files:
- filename contains `daily` and `activity`
- loaded into `raw.daily_activity`
- required columns:
  - `Id`
  - `ActivityDate`
  - `TotalSteps`
  - `Calories`

Sleep files (optional):
- filename contains `sleep`
- loaded into `raw.sleep`
- expected columns:
  - `Id`
  - `SleepDay`
  - `TotalMinutesAsleep`

---

## Key Metrics

The pipeline calculates user-level engagement metrics:

- **baseline_steps**  
  Median daily steps across a user's first 14 active days.

- **steps_pct_of_baseline**  
  Daily steps divided by the baseline level.

- **steps_delta_from_baseline**  
  Absolute deviation from the baseline activity level.

- **is_baseline_window**  
  Flag indicating whether a record falls within the baseline period.

---

## dbt Models

The transformation layer produces analytics-ready tables:

- `user_daily_activity`  
  Cleaned daily activity data.

- `user_baseline_activity`  
  Baseline step calculations for each user.

- `user_activity_deviation`  
  Daily activity relative to baseline behavior.

---

## Concepts Demonstrated

- Batch ingestion pipelines in Python
- Relational data modeling in Postgres
- Analytics engineering using dbt
- Data quality testing with dbt tests
- Local containerized infrastructure with Docker
- Lightweight analytics dashboards with Streamlit
