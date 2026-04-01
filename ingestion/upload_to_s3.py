"""Upload local CSV drops to S3 with date partitioning and idempotent manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from ingestion.config import data_drop_dir, get_logger
from ingestion.csv_partition import build_s3_key, list_candidate_files
from ingestion import db
from ingestion.manifest import (
    ensure_s3_manifest_table,
    file_checksum,
    get_s3_manifest_row,
    upsert_s3_manifest,
)
from ingestion.s3io import (
    bucket_name,
    ensure_bucket,
    get_s3_client,
    head_object_meta,
    put_object_with_checksum,
    s3_prefix,
)

log = get_logger(__name__)


def upload_one(
    path: Path,
    engine,
    client,
    bucket: str,
    prefix: str,
) -> tuple[bool, str]:
    """Returns (uploaded_or_skipped_needs_db, s3_key)."""
    key = build_s3_key(prefix, path)
    checksum = file_checksum(path)
    row = get_s3_manifest_row(engine, key)
    if row and row["checksum"] == checksum:
        log.info("Skip upload (idempotent manifest): s3://%s/%s", bucket, key)
        return False, key

    head = head_object_meta(client, bucket, key)
    if head:
        meta = (head.get("Metadata") or {}) if isinstance(head, dict) else {}
        if (meta.get("sha256") or "").lower() == checksum.lower():
            etag = head.get("ETag")
            if isinstance(etag, str):
                etag = etag.strip('"')
            sz = int(head.get("ContentLength") or path.stat().st_size)
            upsert_s3_manifest(engine, key, path.name, checksum, etag, sz)
            log.info("Skip upload (S3 metadata matches): s3://%s/%s", bucket, key)
            return False, key

    body = path.read_bytes()
    etag = put_object_with_checksum(client, bucket, key, body, checksum, log)
    upsert_s3_manifest(engine, key, path.name, checksum, etag, len(body))
    return True, key


def run_upload(data_dir: Path | None = None) -> int:
    root = data_dir or data_drop_dir()
    files = list_candidate_files(root)
    if not files:
        log.warning("No wearable CSV files found under %s", root)
        return 0

    try:
        engine = db.get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        log.error("Postgres required for S3 upload manifest: %s", e)
        return 1

    ensure_s3_manifest_table(engine)
    client = get_s3_client()
    bucket = bucket_name()
    ensure_bucket(client, bucket, log)
    prefix = s3_prefix()

    uploaded = 0
    for path in files:
        did_upload, key = upload_one(path, engine, client, bucket, prefix)
        if did_upload:
            uploaded += 1
        log.info("Processed %s -> s3://%s/%s", path.name, bucket, key)

    log.info("Upload complete: %s file(s) newly uploaded, %s total candidates", uploaded, len(files))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload CSV drops to S3 (partitioned, idempotent).")
    parser.add_argument("--data-dir", default=None, help="Override DATA_DROP_DIR")
    args = parser.parse_args()
    data = Path(args.data_dir) if args.data_dir else data_drop_dir()
    return run_upload(data_dir=data)


if __name__ == "__main__":
    raise SystemExit(main())
