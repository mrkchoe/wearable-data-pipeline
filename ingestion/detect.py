"""Detect local CSV files that need processing (new or changed vs manifests)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.exc import OperationalError

from ingestion.config import data_drop_dir, get_logger
from ingestion.csv_partition import build_s3_key, list_candidate_files, table_name_from_path
from ingestion import db
from ingestion.manifest import (
    ensure_manifest_table,
    ensure_s3_manifest_table,
    file_checksum,
    get_manifest_row,
    get_s3_manifest_row,
    upsert_s3_manifest,
)
from ingestion.s3io import bucket_name, get_s3_client, head_object_meta, s3_prefix


log = get_logger(__name__)


def needs_s3_upload(path: Path, engine) -> bool:
    key = build_s3_key(s3_prefix(), path)
    checksum = file_checksum(path)
    row = get_s3_manifest_row(engine, key)
    if row and row["checksum"] == checksum:
        log.debug("Skip S3 (manifest match): %s", key)
        return False
    try:
        client = get_s3_client()
        bucket = bucket_name()
        head = head_object_meta(client, bucket, key)
    except Exception as e:  # noqa: BLE001
        log.warning("S3 head_object failed for %s; treating as upload needed: %s", key, e)
        return True
    if head:
        meta = (head.get("Metadata") or {}) if isinstance(head, dict) else {}
        remote = (meta.get("sha256") or "").lower()
        if remote == checksum.lower():
            log.info("S3 object already has matching sha256 metadata; syncing manifest only: %s", key)
            etag = head.get("ETag")
            if isinstance(etag, str):
                etag = etag.strip('"')
            sz = int(head.get("ContentLength") or path.stat().st_size)
            upsert_s3_manifest(engine, key, path.name, checksum, etag, sz)
            return False
    return True


def needs_postgres_reload(path: Path, engine, use_manifest: bool) -> bool:
    if not use_manifest:
        return True
    row = get_manifest_row(engine, path.name)
    checksum = file_checksum(path)
    if row and row["checksum"] == checksum:
        return False
    return True


def detect_files(
    data_dir: Path | None = None,
    engine=None,
    check_s3: bool = True,
    check_pg: bool = False,
    use_manifest_pg: bool = True,
) -> dict:
    """Return JSON-serializable summary of pending work."""
    root = data_dir or data_drop_dir()
    files = list_candidate_files(root)
    pending_s3: list[str] = []
    pending_pg: list[str] = []
    errors: list[str] = []

    if engine is None:
        try:
            engine = db.get_engine()
            with engine.connect() as conn:
                from sqlalchemy import text

                conn.execute(text("SELECT 1"))
        except OperationalError as e:
            log.warning("Postgres unavailable; manifest checks skipped: %s", e)
            engine = None

    if engine is not None:
        ensure_manifest_table(engine)
        ensure_s3_manifest_table(engine)

    for path in files:
        try:
            if check_s3 and engine is not None:
                if needs_s3_upload(path, engine):
                    pending_s3.append(path.name)
            elif check_s3:
                pending_s3.append(path.name)
            if check_pg and engine is not None:
                if needs_postgres_reload(path, engine, use_manifest_pg):
                    pending_pg.append(path.name)
        except Exception as e:  # noqa: BLE001
            msg = f"{path.name}: {e}"
            log.error("Detect failed for %s: %s", path.name, e)
            errors.append(msg)

    summary = {
        "data_dir": str(root.resolve()),
        "candidates": [p.name for p in files],
        "pending_s3_upload": pending_s3,
        "pending_postgres": pending_pg,
        "errors": errors,
        "has_pending_s3": bool(pending_s3),
        "has_pending_postgres": bool(pending_pg),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect new/changed CSV drops.")
    parser.add_argument("--data-dir", default=None, help="Override DATA_DROP_DIR")
    parser.add_argument("--json", action="store_true", help="Print JSON summary only.")
    parser.add_argument(
        "--check-postgres",
        action="store_true",
        help="Include postgres manifest delta in pending_postgres.",
    )
    args = parser.parse_args()
    data = Path(args.data_dir) if args.data_dir else data_drop_dir()
    summary = detect_files(data_dir=data, check_pg=args.check_postgres)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        log.info(
            "candidates=%s pending_s3=%s pending_pg=%s errors=%s",
            summary["candidates"],
            summary["pending_s3_upload"],
            summary["pending_postgres"],
            summary["errors"],
        )
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
