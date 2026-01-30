"""Shared database connection: supports DATABASE_URL or DB_* env vars (e.g. cloud Postgres)."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_connection_url() -> str:
    """Build Postgres URL from DATABASE_URL or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD."""
    url = os.getenv("DATABASE_URL")
    if url:
        # Ensure scheme is postgresql for SQLAlchemy (postgres:// -> postgresql://)
        parsed = urlparse(url)
        if parsed.scheme == "postgres":
            url = url.replace("postgres://", "postgresql://", 1)
        elif parsed.scheme != "postgresql":
            url = "postgresql+" + (url if "://" in url else "psycopg2://" + url)
        if "postgresql://" in url and "+" not in url.split("://")[0]:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "wearable")
    user = os.getenv("DB_USER", "wearable")
    password = os.getenv("DB_PASSWORD", "wearable")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def get_engine() -> Engine:
    """Create SQLAlchemy engine from DATABASE_URL or DB_* env vars."""
    return create_engine(get_connection_url())


def get_connection_info() -> tuple[str, str, str]:
    """Return (dbname, host, port) for display; best-effort from URL or env."""
    url = os.getenv("DATABASE_URL")
    if url:
        parsed = urlparse(url)
        return (parsed.path.lstrip("/") or "wearable", parsed.hostname or "localhost", str(parsed.port or 5432))
    return (
        os.getenv("DB_NAME", "wearable"),
        os.getenv("DB_HOST", "localhost"),
        os.getenv("DB_PORT", "5432"),
    )
