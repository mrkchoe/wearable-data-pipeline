"""Load wearable CSVs into Postgres raw schema."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


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
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "wearable")
    user = os.getenv("DB_USER", "wearable")
    password = os.getenv("DB_PASSWORD", "wearable")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url), dbname, host, port


def _ingest_csv(path: Path, schema: str, if_exists: str) -> None:
    engine, dbname, host, port = _build_engine()
    table_name = _table_name_from_path(path)

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
    print(f"Loaded {len(dataframe)} rows into {schema}.{table_name}")


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
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    schema = _sanitize_identifier(args.schema)
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    for csv_path in csv_files:
        _ingest_csv(csv_path, schema, args.if_exists)


if __name__ == "__main__":
    main()
