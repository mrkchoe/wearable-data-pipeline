"""Storage abstraction for raw data: Local (implemented), S3/GCS (stubs)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class Storage(ABC):
    """Abstract interface for listing and reading CSV files (e.g. local dir, S3, GCS)."""

    @abstractmethod
    def list_csv_keys(self) -> List[str]:
        """Return list of keys (filenames) for CSV files to ingest."""
        ...

    @abstractmethod
    def get_content(self, key: str) -> bytes:
        """Return raw bytes for the given key."""
        ...

    def get_path(self, key: str) -> Path | None:
        """Return local Path if this key is a local file; else None (caller uses get_content)."""
        return None


class LocalStorage(Storage):
    """Read from a local directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"Storage root not found: {self.root}")

    def list_csv_keys(self) -> List[str]:
        return sorted(f.name for f in self.root.glob("*.csv"))

    def get_content(self, key: str) -> bytes:
        path = self.root / key
        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        return path.read_bytes()

    def get_path(self, key: str) -> Path | None:
        path = self.root / key
        return path if path.exists() else None


class S3Storage(Storage):
    """Stub for S3. Set STORAGE_BACKEND=s3, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, (optional) S3_PREFIX)."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "S3 storage not implemented. Install boto3 and set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET. "
            "Use STORAGE_BACKEND=local for local data."
        )

    def list_csv_keys(self) -> List[str]:
        raise NotImplementedError("S3 not implemented")

    def get_content(self, key: str) -> bytes:
        raise NotImplementedError("S3 not implemented")


class GCSStorage(Storage):
    """Stub for Google Cloud Storage. Set STORAGE_BACKEND=gcs, GCS_BUCKET, and credentials."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "GCS storage not implemented. Install google-cloud-storage and set GCS_BUCKET and credentials. "
            "Use STORAGE_BACKEND=local for local data."
        )

    def list_csv_keys(self) -> List[str]:
        raise NotImplementedError("GCS not implemented")

    def get_content(self, key: str) -> bytes:
        raise NotImplementedError("GCS not implemented")


def get_storage(data_dir: Path | str) -> Storage:
    """Return Storage for the configured backend (env STORAGE_BACKEND: local, s3, gcs). Default: local."""
    backend = (os.getenv("STORAGE_BACKEND") or "local").strip().lower()
    if backend == "local":
        return LocalStorage(data_dir)
    if backend == "s3":
        return S3Storage()  # type: ignore
    if backend == "gcs":
        return GCSStorage()  # type: ignore
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend}. Use local, s3, or gcs.")
