"""Pipeline runner: ingestion + dbt with run tracking and structured JSON logging."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Allow running as script: python ingestion/runner.py
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.exc import OperationalError

from ingestion import db
from ingestion.run_tracker import (
    end_run,
    ensure_pipeline_runs_table,
    get_engine,
    start_run,
)


def _log_json(run_id: str, step: str, status: str, duration_ms: int | None = None) -> None:
    payload = {"run_id": run_id, "step": step, "status": status}
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    print(json.dumps(payload), flush=True)


def _print_error_report(run_id: str, step: str, error_summary: str) -> None:
    print(
        f"\n--- Pipeline failure ---\nrun_id: {run_id}\nstep: {step}\nerror: {error_summary}\n",
        file=sys.stderr,
        flush=True,
    )


def _run_ingest(data_dir: str, use_manifest: bool) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "ingestion.ingest",
        "--data-dir",
        data_dir,
    ]
    if use_manifest:
        cmd.append("--use-manifest")
    return subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True)


def _run_dbt() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["dbt", "run"],
        cwd=_REPO_ROOT / "dbt",
        capture_output=True,
        text=True,
        env={**os.environ},
    )


def main() -> int:
    data_dir = os.getenv("PIPELINE_DATA_DIR", "data_lake")
    use_manifest = os.getenv("PIPELINE_USE_MANIFEST", "0").lower() in ("1", "true", "yes")
    engine = get_engine()
    dbname, host, port = db.get_connection_info()

    try:
        ensure_pipeline_runs_table(engine)
    except OperationalError:
        print(
            f"Error: Cannot connect to Postgres at {host}:{port}/{dbname}. "
            "Is it running? Set DATABASE_URL or DB_* env vars.",
            file=sys.stderr,
        )
        return 1

    run_id = start_run(engine)
    _log_json(run_id, "pipeline", "started")

    failed_step = None
    error_summary = None

    # Step: ingest
    t0 = time.perf_counter()
    _log_json(run_id, "ingest", "started")
    result = _run_ingest(data_dir, use_manifest)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    if result.returncode != 0:
        failed_step = "ingest"
        error_summary = result.stderr or result.stdout or f"exit code {result.returncode}"
        _log_json(run_id, "ingest", "failure", duration_ms)
        end_run(engine, run_id, "failure", error_summary)
        _print_error_report(run_id, failed_step, error_summary)
        return 1
    _log_json(run_id, "ingest", "success", duration_ms)

    # Step: dbt run
    t0 = time.perf_counter()
    _log_json(run_id, "dbt_run", "started")
    result = _run_dbt()
    duration_ms = int((time.perf_counter() - t0) * 1000)
    if result.returncode != 0:
        failed_step = "dbt_run"
        error_summary = result.stderr or result.stdout or f"exit code {result.returncode}"
        _log_json(run_id, "dbt_run", "failure", duration_ms)
        end_run(engine, run_id, "failure", error_summary)
        _print_error_report(run_id, failed_step, error_summary)
        return 1
    _log_json(run_id, "dbt_run", "success", duration_ms)

    end_run(engine, run_id, "success", None)
    _log_json(run_id, "pipeline", "success")
    return 0


if __name__ == "__main__":
    sys.exit(main())
