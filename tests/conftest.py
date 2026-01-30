"""Pytest fixtures. Engine fixture skips if Postgres is not available."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Ensure repo root is on path when running tests
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _make_engine() -> Engine:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        pytest.skip("psycopg2 not installed")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "wearable")
    user = os.getenv("DB_USER", "wearable")
    password = os.getenv("DB_PASSWORD", "wearable")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Postgres engine; skip if DB is not reachable."""
    try:
        eng = _make_engine()
    except Exception as e:
        pytest.skip(f"Postgres not available: {e}")
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Postgres not reachable: {e}")
    return eng
