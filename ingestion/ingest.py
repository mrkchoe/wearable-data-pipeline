"""Load wearable CSVs into Postgres raw schema. Supports idempotent ingest via manifest."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Allow running as script: python ingestion/ingest.py
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ingestion import db
from ingestion.manifest import (
    ensure_manifest_table,
    file_checksum,
    get_manifest_row,
    upsert_manifest,
)


def _sanitize_identifier(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValueError(f"Invalid identifier derived from '{value}'.")
    return normalized


def _table_name_from_path(path: Path) -> str:
    base_name = _sanitize_identifier(path.stem)
    if "daily" in base_name and "activity" in base_name:
        return "daily_activity"
    if "sleep" in base_name:
        return "sleep"
    return base_name


def _build_engine() -> tuple:
    engine = db.get_engine()
    dbname, host, port = db.get_connection_info()
    return engine, dbname, host, port


def _ingest_csv(
    path: Path,
    schema: str,
    if_exists: str,
    use_manifest: bool,
    engine=None,
) -> bool:
    """Load one CSV into raw schema. Returns True if loaded, False if skipped (manifest idempotent)."""
    if engine is None:
        engine, dbname, host, port = _build_engine()
    else:
        dbname, host, port = os.getenv("DB_NAME", "wearable"), os.getenv("DB_HOST", "localhost"), os.getenv("DB_PORT", "5432")
    table_name = _table_name_from_path(path)
    source_filename = path.name

    if use_manifest:
        ensure_manifest_table(engine)
        checksum = file_checksum(path)
        existing = get_manifest_row(engine, source_filename)
        if existing and existing["checksum"] == checksum:
            print(f"Skipping '{source_filename}' (unchanged checksum {checksum[:16]}...)")
            return False

    print(f"Loading '{path.name}' into {schema}.{table_name} ({host}:{port}/{dbname})")
    dataframe = pd.read_csv(path)

    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        if if_exists == "replace":
            connection.execute(
                text(f"DROP TABLE IF EXISTS {schema}.{table_name} CASCADE")
            )

    dataframe.to_sql(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists=if_exists,
        index=False,
    )
    row_count = len(dataframe)
    print(f"Loaded {row_count} rows into {schema}.{table_name}")

    if use_manifest:
        checksum = file_checksum(path)
        upsert_manifest(engine, source_filename, checksum, row_count, "success")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest wearable CSVs into Postgres.")
    parser.add_argument("--data-dir", default="data", help="Directory with CSV drops.")
    parser.add_argument("--schema", default="raw", help="Target Postgres schema.")
    parser.add_argument(
        "--if-exists",
        default="replace",
        choices=["replace", "append", "fail"],
        help="Behavior when a table already exists.",
    )
    parser.add_argument(
        "--use-manifest",
        action="store_true",
        help="Use raw_ingest_manifest for idempotency; skip files with same checksum.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    schema = _sanitize_identifier(args.schema)
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    engine, dbname, host, port = _build_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        print(
            f"Error: Cannot connect to Postgres at {host}:{port}/{dbname}. "
            "Is it running? Try: docker compose up -d",
            file=sys.stderr,
        )
        sys.exit(1)

    for csv_path in csv_files:
        _ingest_csv(csv_path, schema, args.if_exists, args.use_manifest, engine=engine)


if __name__ == "__main__":
    main()
