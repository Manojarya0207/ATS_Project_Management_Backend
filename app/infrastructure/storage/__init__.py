"""Storage abstraction.

Business logic depends only on the :class:`StorageBackend` protocol; the
concrete backend (local disk, S3, Cloudflare R2, Azure Blob) is selected by
``Settings.storage_backend`` and injected during application startup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from fastapi import UploadFile

from app.core.config import Settings


@dataclass(frozen=True)
class StoredFile:
    """Result of a successful upload."""

    key: str  # backend-specific identifier (filename / object key)
    size_bytes: int


@runtime_checkable
class StorageBackend(Protocol):
    async def save(self, upload: UploadFile, *, max_size_bytes: int) -> StoredFile:
        """Persist an upload stream. Raises ``ValidationAppError`` when the
        stream exceeds ``max_size_bytes`` (partial data must be cleaned up)."""
        ...

    async def delete(self, key: str) -> None:
        """Remove a stored object. Missing objects are not an error."""
        ...

    def local_path(self, key: str) -> Path | None:
        """Filesystem path when the backend is disk-based, else ``None``.

        Used to serve downloads with ``FileResponse``; remote backends return
        ``None`` and downloads stream via :meth:`open` (or a presigned URL).
        """
        ...


def get_storage(settings: Settings) -> StorageBackend:
    """Factory: resolve the configured storage backend."""
    backend = settings.storage_backend.lower()
    if backend == "local":
        from app.infrastructure.storage.local import LocalStorage

        return LocalStorage(settings)
    if backend in ("s3", "r2"):
        from app.infrastructure.storage.s3 import S3Storage

        return S3Storage(settings)
    if backend == "azure":
        from app.infrastructure.storage.azure import AzureBlobStorage

        return AzureBlobStorage(settings)
    raise ValueError(f"Unknown storage backend: {settings.storage_backend!r}")
