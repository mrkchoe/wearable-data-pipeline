# Phase 2: Productionization Design Decisions

## Current state (pre–Phase 2)

- **Ingestion**: Single script `ingestion/ingest.py` reads CSVs from a configurable `--data-dir` (default `data/`), maps filenames to table names (`daily_activity`, `sleep`), and loads into Postgres `raw` schema. No idempotency; re-run replaces tables.
- **dbt**: Staging models read from `raw.daily_activity` and `raw.sleep`; marts build user baselines and deviations. CI runs `dbt deps`, `dbt run`, `dbt test` after ingesting from `sample_data/`.
- **CI**: GitHub Actions runs on push/PR: Postgres 16 service, Python 3.11, ingest from `sample_data/`, then dbt. No run tracking or failure alerting.

## Phase 2 plan (3–5 PRs)

| PR | Scope | Key files |
|----|--------|-----------|
| **PR1** | Durable raw landing zone | `data_lake/`, `ingestion/manifest.py`, `ingestion/ingest.py`, DDL for `ops.raw_ingest_manifest` |
| **PR2** | Operational run tracking + observability | `ingestion/run_tracker.py`, `ingestion/runner.py`, DDL for `ops.pipeline_runs`, README + docs |
| **PR3** | Scheduling + alerting (cron + failure notification) | `.github/workflows/scheduled.yml`, optional issue/email on failure |
| **PR4** | Prod-like container entrypoint | `make run-prod`, Dockerfile or compose override, deterministic DDL application |
| **PR5** (optional) | Storage interface abstraction | `ingestion/storage.py` (Local impl, S3/GCS stubs) |

## Design decisions

### 1. Raw landing zone (`data_lake/`)

- **Decision**: Use a local directory `data_lake/` as the canonical “raw” landing zone for production-like runs.
- **Rationale**: Keeps a single, explicit place for raw drops; `data/` remains usable for ad-hoc local use; CI can still use `sample_data/` or `data_lake/` with seeded files.
- **Default**: Ingestion defaults to `data_lake/` when using manifest mode; `--data-dir` overrides for local/CI (e.g. `sample_data`).

### 2. Manifest table (`ops.raw_ingest_manifest`)

- **Decision**: Store one row per successfully ingested file: `source_filename`, `checksum`, `ingested_at`, `row_count`, `status`.
- **Schema**: Use an `ops` schema for operational tables so `raw` stays strictly for source data.
- **Idempotency**: Before loading a file, compute content checksum (SHA-256); if a row exists with same `source_filename` and `checksum`, skip. Otherwise load and upsert manifest row with `status = 'success'`.

### 3. Run tracking (`ops.pipeline_runs`)

- **Decision**: Record each pipeline run with `run_id` (UUID), `started_at`, `finished_at`, `status` (`running` | `success` | `failure`), `error_summary` (nullable text).
- **Structured logs**: Emit JSON lines to stdout: `{"run_id": "...", "step": "ingest"|"dbt_run"|..., "status": "started"|"success"|"failure", "duration_ms": N}`.
- **Failure**: On any step failure, update run to `failure`, set `error_summary`, print a short error report to stderr, exit with code 1.

### 4. DDL application

- **Decision**: Apply DDL for `ops.raw_ingest_manifest` and `ops.pipeline_runs` from Python at runtime (`CREATE SCHEMA IF NOT EXISTS ops`; `CREATE TABLE IF NOT EXISTS ...`).
- **Rationale**: No separate migration runner for Phase 2; keeps local-first and CI simple. Phase 4 can introduce a single “migrate” step that runs these DDLs deterministically before the pipeline.

### 5. Local-first + prod-like

- **Decision**: Default developer experience remains “docker compose + data/ or sample_data + ingest + dbt”. Prod-like behavior is opt-in via env (e.g. `PIPELINE_USE_MANIFEST=1`, `PIPELINE_DATA_DIR=data_lake`) or a single entrypoint (`make run-prod`) that sets these and runs the pipeline with manifest and run tracking.

---

## Changes made (Phase 2 items 1 & 2)

- **data_lake/**: Canonical raw landing zone directory; `.gitkeep` committed, contents gitignored.
- **ops.raw_ingest_manifest**: DDL in `ingestion/manifest.py`; columns: source_filename, checksum, ingested_at, row_count, status. Applied via `ensure_manifest_table(engine)`.
- **Idempotent ingest**: `ingestion/ingest.py` supports `--use-manifest`; before load, computes SHA-256 checksum and skips if manifest already has same filename+checksum; after load, upserts manifest row.
- **ops.pipeline_runs**: DDL in `ingestion/run_tracker.py`; columns: run_id (UUID), started_at, finished_at, status, error_summary. Applied via `ensure_pipeline_runs_table(engine)`.
- **Pipeline runner**: `ingestion/runner.py` runs ingest then dbt; logs JSON lines (run_id, step, status, duration_ms); on failure updates run with error_summary, prints compact error report to stderr, exits 1.
- **Makefile**: `make test` (pytest), `make run-prod` (runner with data_lake + manifest).
- **Tests**: `tests/test_manifest.py` (unit: checksum, manifest upsert/get); `tests/test_ingest_integration.py` (integration: ingest twice, verify manifest idempotency). Integration tests skip if Postgres/psycopg2 unavailable.
- **CI**: Run `pytest tests/ -v` after ingest; use `python -m ingestion.ingest` for consistency.
