# Deployment and cloud

## Cloud Postgres

The pipeline uses **DATABASE_URL** or **DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD** for all DB connections (ingestion, run tracking, dbt).

- **Local**: Use defaults or `docker compose up -d`; no env needed.
- **Cloud (RDS, Cloud SQL, etc.)**: Set `DATABASE_URL` (e.g. `postgresql://user:pass@host:5432/dbname`) or set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`. The same code runs against local or cloud Postgres.

dbt uses the same env vars via `dbt/profiles.yml` (env_var with defaults).

## Scheduled run (GitHub Actions)

`.github/workflows/scheduled.yml` runs the pipeline on a cron (default: daily 06:00 UTC) and on `workflow_dispatch`.

**Setup**

1. In the repo: **Settings → Secrets and variables → Actions**.
2. Add secrets (use either option):
   - **Option A**: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
   - **Option B**: `DATABASE_URL` (full URL; ingestion uses it; dbt still needs DB_* or a profile that reads from one env).
3. The workflow uses these secrets for ingest, pytest, and dbt. No Postgres service is started in the job; the DB must be reachable from GitHub (e.g. cloud Postgres with allowed IPs or a tunnel).

To test without cloud DB, run the **ci** workflow (push/PR); it uses the built-in Postgres service.

## Storage abstraction

`ingestion/storage.py` defines a **Storage** interface:

- **LocalStorage** (default): reads from a local directory; use `STORAGE_BACKEND=local` or unset.
- **S3Storage** / **GCSStorage**: stubs; raise `NotImplementedError` with a short message. To add S3/GCS later: implement `list_csv_keys()` and `get_content(key)` and wire ingest to use `get_storage()` when `STORAGE_BACKEND` is set.

Ingestion today is path-based (`--data-dir`); the storage layer is ready for future S3/GCS wiring.

## Container (Docker)

**Build and run**

```bash
docker build -t wearable-pipeline .
docker run --rm \
  -e DATABASE_URL="postgresql://user:pass@host:5432/wearable" \
  -e PIPELINE_DATA_DIR=/app/sample_data \
  wearable-pipeline
```

Or with DB_*:

```bash
docker run --rm \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_NAME=wearable \
  -e DB_USER=wearable \
  -e DB_PASSWORD=wearable \
  -e PIPELINE_DATA_DIR=/app/sample_data \
  wearable-pipeline
```

**Scheduled job (Cloud Run Jobs, ECS, etc.)**

1. Build and push the image to your registry.
2. Create a job that runs the image on a schedule (e.g. daily).
3. Set env (or secrets): `DATABASE_URL` or `DB_*`, and optionally `PIPELINE_DATA_DIR`, `PIPELINE_USE_MANIFEST=1`.
4. Ensure the job has network access to your Postgres and (if you add S3/GCS) credentials for storage.

Data can be provided by mounting a volume, copying CSVs into the image, or (later) reading from object storage via the storage abstraction.
