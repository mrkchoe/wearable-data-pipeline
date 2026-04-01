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
    """List/read CSV keys from an S3-compatible bucket (AWS S3 or MinIO via S3_ENDPOINT_URL)."""

    def __init__(self) -> None:
        from ingestion.s3io import bucket_name, get_s3_client, s3_prefix

        self._client = get_s3_client()
        self._bucket = bucket_name()
        self._prefix = (s3_prefix().strip("/") + "/") if s3_prefix() else ""

    def list_csv_keys(self) -> List[str]:
        from ingestion.s3io import iter_objects_under

        keys: List[str] = []
        for obj in iter_objects_under(self._client, self._bucket, self._prefix):
            key = obj["Key"]
            if key.lower().endswith(".csv"):
                keys.append(key.rsplit("/", 1)[-1])
        return sorted(set(keys))

    def get_content(self, key: str) -> bytes:
        from ingestion.s3io import download_object_bytes

        # If key is bare filename, find first matching object under prefix (best-effort).
        candidates = [k for k in self._list_full_keys() if k.lower().endswith(".csv") and k.rsplit("/", 1)[-1] == key]
        s3_key = candidates[0] if candidates else f"{self._prefix}{key}"
        return download_object_bytes(self._client, self._bucket, s3_key)

    def _list_full_keys(self) -> List[str]:
        from ingestion.s3io import iter_objects_under

        return [o["Key"] for o in iter_objects_under(self._client, self._bucket, self._prefix)]


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
