"""Unit tests for manifest: checksum and idempotency logic."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ingestion.manifest import (
    ensure_manifest_table,
    file_checksum,
    get_manifest_row,
    upsert_manifest,
)


def test_file_checksum_same_content_same_hash() -> None:
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as f:
        f.write(b"a,b\n1,2\n")
        path = Path(f.name)
    try:
        assert file_checksum(path) == file_checksum(path)
        h1 = file_checksum(path)
        path.write_bytes(b"a,b\n1,2\n")  # same bytes so checksum unchanged
        assert file_checksum(path) == h1
    finally:
        path.unlink(missing_ok=True)


def test_file_checksum_different_content_different_hash() -> None:
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as f:
        f.write(b"a,b\n1,2\n")
        path1 = Path(f.name)
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as f:
        f.write(b"a,b\n1,3\n")
        path2 = Path(f.name)
    try:
        assert file_checksum(path1) != file_checksum(path2)
    finally:
        path1.unlink(missing_ok=True)
        path2.unlink(missing_ok=True)


def test_file_checksum_deterministic() -> None:
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as f:
        f.write(b"Id,SleepDay\n1001,01/20/2026\n")
        path = Path(f.name)
    try:
        # SHA-256 of this content is fixed
        h = file_checksum(path)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
    finally:
        path.unlink(missing_ok=True)


def test_manifest_ensure_and_upsert_get(engine: "pytest.fixture") -> None:
    from sqlalchemy.engine import Engine

    ensure_manifest_table(engine)
    upsert_manifest(engine, "test_file.csv", "abc123", 10, "success")
    row = get_manifest_row(engine, "test_file.csv")
    assert row is not None
    assert row["source_filename"] == "test_file.csv"
    assert row["checksum"] == "abc123"
    assert row["row_count"] == 10
    assert row["status"] == "success"


def test_manifest_idempotent_skip_when_same_checksum(engine: "pytest.fixture") -> None:
    from sqlalchemy.engine import Engine

    ensure_manifest_table(engine)
    upsert_manifest(engine, "idempotent.csv", "same_checksum", 5, "success")
    row_before = get_manifest_row(engine, "idempotent.csv")
    upsert_manifest(engine, "idempotent.csv", "same_checksum", 5, "success")
    row_after = get_manifest_row(engine, "idempotent.csv")
    assert row_before["checksum"] == row_after["checksum"]
    assert row_after["row_count"] == 5
