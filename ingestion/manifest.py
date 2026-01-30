"""Raw ingest manifest: DDL and helpers for idempotent ingestion."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

OPS_SCHEMA = "ops"
MANIFEST_TABLE = "raw_ingest_manifest"

DDL_RAW_INGEST_MANIFEST = f"""
CREATE SCHEMA IF NOT EXISTS {OPS_SCHEMA};
CREATE TABLE IF NOT EXISTS {OPS_SCHEMA}.{MANIFEST_TABLE} (
    source_filename TEXT NOT NULL,
    checksum        TEXT NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    row_count       INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'success',
    PRIMARY KEY (source_filename)
);
"""


def ensure_manifest_table(engine: Engine) -> None:
    """Create ops schema and raw_ingest_manifest table if they do not exist."""
    with engine.begin() as conn:
        conn.execute(text(DDL_RAW_INGEST_MANIFEST))


def file_checksum(path: Path) -> str:
    """Compute SHA-256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_manifest_row(engine: Engine, source_filename: str) -> dict | None:
    """Return the latest manifest row for source_filename, or None."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT source_filename, checksum, ingested_at, row_count, status "
                f"FROM {OPS_SCHEMA}.{MANIFEST_TABLE} WHERE source_filename = :fn"
            ),
            {"fn": source_filename},
        ).fetchone()
    if row is None:
        return None
    return {
        "source_filename": row[0],
        "checksum": row[1],
        "ingested_at": row[2],
        "row_count": row[3],
        "status": row[4],
    }


def upsert_manifest(
    engine: Engine,
    source_filename: str,
    checksum: str,
    row_count: int,
    status: str = "success",
) -> None:
    """Insert or update manifest row for this file."""
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {OPS_SCHEMA}.{MANIFEST_TABLE}
                    (source_filename, checksum, row_count, status)
                VALUES (:fn, :checksum, :row_count, :status)
                ON CONFLICT (source_filename)
                DO UPDATE SET
                    checksum = EXCLUDED.checksum,
                    ingested_at = now(),
                    row_count = EXCLUDED.row_count,
                    status = EXCLUDED.status;
                """
            ),
            {
                "fn": source_filename,
                "checksum": checksum,
                "row_count": row_count,
                "status": status,
            },
        )
