"""Azure Blob Storage backend (adapter stub).

Configured via ``AZURE_CONTAINER`` and ``AZURE_CONNECTION_STRING``. Requires
``azure-storage-blob`` (add to your deployment's dependencies when enabling).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import anyio.to_thread
from fastapi import UploadFile

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.exceptions import ValidationAppError
from app.infrastructure.storage import StoredFile


class AzureBlobStorage:
    def __init__(self, settings: Settings) -> None:
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Azure storage requires azure-storage-blob — pip install azure-storage-blob"
            ) from exc
        if not settings.azure_connection_string or not settings.azure_container:
            raise ValueError(
                "AZURE_CONNECTION_STRING and AZURE_CONTAINER must be configured "
                "for the azure storage backend"
            )
        service = BlobServiceClient.from_connection_string(settings.azure_connection_string)
        self.container = service.get_container_client(settings.azure_container)

    def _key_for(self, original_filename: str) -> str:
        suffix = Path(original_filename or "").suffix[:16]
        return f"{uuid.uuid4().hex}{suffix}"

    async def save(self, upload: UploadFile, *, max_size_bytes: int) -> StoredFile:
        data = await upload.read(max_size_bytes + 1)
        if len(data) > max_size_bytes:
            raise ValidationAppError(
                f"File exceeds maximum size of {max_size_bytes} bytes",
                code=ErrorCode.file_too_large,
                field="file",
            )
        key = self._key_for(upload.filename or "")
        await anyio.to_thread.run_sync(lambda: self.container.upload_blob(name=key, data=data))
        return StoredFile(key=key, size_bytes=len(data))

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(lambda: self.container.delete_blob(key))

    def local_path(self, key: str) -> Path | None:
        return None
