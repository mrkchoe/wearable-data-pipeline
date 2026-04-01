"""Load .env from repo root, expose settings, and configure logging."""

from __future__ import annotations

import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    if load_dotenv is None:
        return
    env_path = _REPO_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    load_dotenv(_REPO_ROOT / "infra" / ".env", override=False)


_load_env()


def get_logger(name: str) -> logging.Logger:
    level = (os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )
    return logging.getLogger(name)


def repo_root() -> Path:
    return _REPO_ROOT


def data_drop_dir() -> Path:
    path = Path(os.getenv("DATA_DROP_DIR") or os.getenv("PIPELINE_DATA_DIR") or "sample_data")
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path
