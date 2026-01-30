"""Pipeline run tracking: DDL and helpers for ops.pipeline_runs."""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ingestion import db

OPS_SCHEMA = "ops"
PIPELINE_RUNS_TABLE = "pipeline_runs"

DDL_PIPELINE_RUNS = f"""
CREATE SCHEMA IF NOT EXISTS {OPS_SCHEMA};
CREATE TABLE IF NOT EXISTS {OPS_SCHEMA}.{PIPELINE_RUNS_TABLE} (
    run_id         UUID PRIMARY KEY,
    started_at     TIMESTAMPTZ NOT NULL,
    finished_at    TIMESTAMPTZ,
    status         TEXT NOT NULL,
    error_summary  TEXT
);
"""


def get_engine() -> Engine:
    return db.get_engine()


def ensure_pipeline_runs_table(engine: Engine) -> None:
    """Create ops schema and pipeline_runs table if they do not exist."""
    with engine.begin() as conn:
        conn.execute(text(DDL_PIPELINE_RUNS))


def start_run(engine: Engine) -> str:
    """Insert a new run with status 'running', return run_id."""
    run_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                f"INSERT INTO {OPS_SCHEMA}.{PIPELINE_RUNS_TABLE} (run_id, started_at, status) "
                "VALUES (:run_id, :started_at, 'running')"
            ),
            {"run_id": run_id, "started_at": datetime.now(timezone.utc)},
        )
    return run_id


def end_run(
    engine: Engine,
    run_id: str,
    status: str,
    error_summary: str | None = None,
) -> None:
    """Update run with finished_at, status, and optional error_summary."""
    with engine.begin() as conn:
        conn.execute(
            text(
                f"UPDATE {OPS_SCHEMA}.{PIPELINE_RUNS_TABLE} "
                "SET finished_at = :finished_at, status = :status, error_summary = :error_summary "
                "WHERE run_id = :run_id"
            ),
            {
                "run_id": run_id,
                "finished_at": datetime.now(timezone.utc),
                "status": status,
                "error_summary": error_summary,
            },
        )


@contextmanager
def tracked_run(engine: Engine) -> Generator[str, None, None]:
    """Context manager: ensure table, start run, yield run_id, then end run on exit (caller sets status)."""
    ensure_pipeline_runs_table(engine)
    run_id = start_run(engine)
    try:
        yield run_id
    finally:
        pass  # Caller must call end_run explicitly so they can set status/error_summary
