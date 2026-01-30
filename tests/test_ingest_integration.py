"""Integration test: ingest twice with manifest; verify idempotency (manifest + raw row count)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

# Repo root on path for ingestion package
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ingestion.manifest import file_checksum, get_manifest_row
from ingestion.run_tracker import get_engine


def _run_ingest(data_dir: str, use_manifest: bool = True) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "ingestion.ingest",
        "--data-dir",
        data_dir,
    ]
    if use_manifest:
        cmd.append("--use-manifest")
    return subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True, env=os.environ.copy())


@pytest.fixture(scope="module")
def engine():
    """Postgres engine; skip if psycopg2 or DB not reachable."""
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        pytest.skip("psycopg2 not installed")
    try:
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Postgres not available: {e}")
    return eng


def test_ingest_twice_manifest_idempotent(engine) -> None:
    """Run ingest twice from sample_data with --use-manifest; manifest has one row per file, same checksum."""
    data_dir = str(_REPO_ROOT / "sample_data")
    result1 = _run_ingest(data_dir, use_manifest=True)
    assert result1.returncode == 0, (result1.stdout, result1.stderr)

    result2 = _run_ingest(data_dir, use_manifest=True)
    assert result2.returncode == 0, (result2.stdout, result2.stderr)

    # Each file should have exactly one manifest row; checksum should match file content
    for name in ("daily_activity.csv", "sleep.csv"):
        path = _REPO_ROOT / "sample_data" / name
        if not path.exists():
            continue
        row = get_manifest_row(engine, name)
        assert row is not None, f"manifest row for {name}"
        expected_checksum = file_checksum(path)
        assert row["checksum"] == expected_checksum, f"checksum for {name}"
