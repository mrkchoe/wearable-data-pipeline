"""Infer dataset type and Hive partition date from wearable CSV filenames and content."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def list_candidate_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    out: list[Path] = []
    for p in sorted(data_dir.glob("*.csv")):
        try:
            table_name_from_path(p)
        except ValueError:
            continue
        out.append(p)
    return out


def table_name_from_path(path: Path) -> str:
    base = path.stem.lower()
    if "daily" in base and "activity" in base:
        return "daily_activity"
    if "sleep" in base:
        return "sleep"
    raise ValueError(f"Cannot classify wearable CSV: {path.name}")


def _parse_activity_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")


def _parse_sleep_day_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")


def partition_date_for_file(path: Path) -> str:
    """Return YYYY-MM-DD partition derived from file content (min calendar date in file)."""
    table = table_name_from_path(path)
    df = pd.read_csv(path)
    if table == "daily_activity":
        if "ActivityDate" not in df.columns:
            raise ValueError(f"{path.name}: missing ActivityDate column")
        dt = _parse_activity_series(df["ActivityDate"]).dropna()
        if dt.empty:
            raise ValueError(f"{path.name}: no parseable ActivityDate values")
        d = dt.min().date()
        return d.isoformat()
    if "SleepDay" not in df.columns:
        raise ValueError(f"{path.name}: missing SleepDay column")
    dt = _parse_sleep_day_series(df["SleepDay"]).dropna()
    if dt.empty:
        raise ValueError(f"{path.name}: no parseable SleepDay values")
    d = dt.min().date()
    return d.isoformat()


def dataset_folder(table: str) -> str:
    if table == "daily_activity":
        return "activity"
    if table == "sleep":
        return "sleep"
    raise ValueError(f"Unknown table for S3 layout: {table}")


def build_s3_key(prefix: str, path: Path) -> str:
    """raw/activity/date=YYYY-MM-DD/<filename>"""
    table = table_name_from_path(path)
    folder = dataset_folder(table)
    part = partition_date_for_file(path)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", path.name)
    p = prefix.strip("/")
    return f"{p}/{folder}/date={part}/{safe_name}"
