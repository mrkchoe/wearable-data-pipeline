# Optional & advanced

Supplement to the [README](../README.md) — details that are useful but not needed for a first run.

## dbt layers

- **Sources:** `staging.daily_activity`, `staging.sleep`
- **Staging:** `stg_daily_activity`, `stg_sleep` (typed, cleaned columns)
- **Marts:** user daily activity, baselines, and deviations; `mart_daily_health_metrics` (steps, distance, calories, sleep efficiency); `mart_data_volume_anomaly` (flags days where row counts deviate >30% from a 7-day trailing average)

Tests live in `dbt/models/**/schema.yml` and the `accepted_range` macro.

## Full configuration

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` or `DB_*` | Warehouse Postgres |
| `DATA_DROP_DIR` | CSV drop folder |
| `S3_ENDPOINT_URL` | MinIO / AWS endpoint |
| `S3_BUCKET`, `S3_PREFIX` | Lake location (default `wearable-lake` / `raw`) |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | MinIO defaults: `minioadmin` / `minioadmin` |
| `PIPELINE_USE_MANIFEST` | Skip unchanged files on re-ingest (default `1`) |
| `LOG_LEVEL` | Python log level |
| `AIRFLOW_UID` | Linux UID for Airflow containers |
| `AIRFLOW__CORE__FERNET_KEY` | Override dev Fernet key for non-dev use |

**Idempotency**

- `ops.raw_ingest_manifest` — skips unchanged local→Postgres loads with `--use-manifest`.
- `ops.s3_upload_manifest` + object `sha256` metadata — skips unchanged uploads.

## S3 layout

Objects are partitioned by the minimum date in each CSV:

- `s3://<bucket>/<prefix>/activity/date=YYYY-MM-DD/<filename>.csv`
- `s3://<bucket>/<prefix>/sleep/date=YYYY-MM-DD/<filename>.csv`

## Host Python (step by step)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp infra/.env.example .env

make up
python -m ingestion.upload_to_s3
python -m ingestion.load_s3_to_staging

mkdir -p ~/.dbt && cp dbt/profiles.yml ~/.dbt/profiles.yml
cd dbt && dbt run && dbt test
```

## Troubleshooting

- **`docker compose` include errors** — Upgrade Compose, or `docker compose -f docker/docker-compose.yml up -d`.
- **Airflow DAG import errors** — `PYTHONPATH` must include the repo root (set in `docker/docker-compose.yml`).
- **MinIO from the host** — Use `S3_ENDPOINT_URL=http://127.0.0.1:9000` in `.env`.
- **Empty staging / dbt source not found** — Run upload + load (or `ingestion.ingest`) before `dbt run`.

## CI

GitHub Actions runs ingest, `pytest`, and `dbt run/test` on push/PR using `sample_data`.
