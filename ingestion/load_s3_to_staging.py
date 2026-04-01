"""Download partitioned CSVs from S3 (or MinIO) and reload Postgres staging tables."""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ingestion.config import get_logger
from ingestion.csv_partition import dataset_folder
from ingestion.ingest import _sanitize_identifier
from ingestion import db
from ingestion.manifest import ensure_manifest_table, upsert_manifest
from ingestion.s3io import (
    bucket_name,
    download_object_bytes,
    get_s3_client,
    iter_objects_under,
    s3_prefix,
)

log = get_logger(__name__)


def _prefix_for_dataset(prefix: str, table: str) -> str:
    base = prefix.strip("/")
    folder = dataset_folder(table)
    return f"{base}/{folder}/"


def _checksum_for_keys_and_shape(keys: list[str], row_count: int) -> str:
    import hashlib

    payload = "|".join(sorted(keys)) + f"|{row_count}"
    return hashlib.sha256(payload.encode()).hexdigest()


def load_staging(
    schema: str = "staging",
    update_manifest: bool = True,
) -> int:
    schema = _sanitize_identifier(schema)
    try:
        engine = db.get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        log.error("Cannot connect to Postgres: %s", e)
        return 1

    client = get_s3_client()
    bucket = bucket_name()
    prefix = s3_prefix()

    if update_manifest:
        ensure_manifest_table(engine)

    for table in ("daily_activity", "sleep"):
        pfx = _prefix_for_dataset(prefix, table)
        dfs: list[pd.DataFrame] = []
        keys: list[str] = []
        for obj in iter_objects_under(client, bucket, pfx):
            key = obj["Key"]
            if not key.lower().endswith(".csv"):
                continue
            raw = download_object_bytes(client, bucket, key)
            df = pd.read_csv(io.BytesIO(raw))
            dfs.append(df)
            keys.append(key)
            log.info("Downloaded %s rows from s3://%s/%s", len(df), bucket, key)

        if not dfs:
            log.warning("No CSV objects under s3://%s/%s", bucket, pfx)
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE'))
            continue

        combined = pd.concat(dfs, ignore_index=True)
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE'))

        combined.to_sql(
            name=table,
            con=engine,
            schema=schema,
            if_exists="append",
            index=False,
        )
        row_count = len(combined)
        log.info("Loaded %s rows into %s.%s", row_count, schema, table)

        if update_manifest:
            pseudo_name = f"s3_bulk::{table}"
            chk = _checksum_for_keys_and_shape(keys, row_count)
            upsert_manifest(engine, pseudo_name, chk, row_count, "success")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Load S3 lake objects into Postgres staging.")
    parser.add_argument(
        "--schema",
        default=os.getenv("STAGING_SCHEMA", "staging"),
        help="Postgres schema for landed tables (default staging).",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Do not update ops.raw_ingest_manifest bulk rows.",
    )
    args = parser.parse_args()
    return load_staging(schema=args.schema, update_manifest=not args.no_manifest)


if __name__ == "__main__":
    raise SystemExit(main())
