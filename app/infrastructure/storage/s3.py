"""S3-compatible storage backend (Amazon S3, Cloudflare R2, MinIO).

Requires the optional ``s3`` dependency group (``pip install .[s3]``).
Configured via ``S3_BUCKET``, ``S3_REGION`` and — for R2/MinIO —
``S3_ENDPOINT_URL``. boto3 is synchronous, so calls are offloaded to worker
threads to keep the event loop free.
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


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "S3 storage requires boto3 — install with: pip install '.[s3]'"
            ) from exc
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET must be configured for the s3/r2 storage backend")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region or None,
            endpoint_url=settings.s3_endpoint_url or None,
        )

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
        await anyio.to_thread.run_sync(
            lambda: self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=upload.content_type or "application/octet-stream",
            )
        )
        return StoredFile(key=key, size_bytes=len(data))

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(
            lambda: self.client.delete_object(Bucket=self.bucket, Key=key)
        )

    def local_path(self, key: str) -> Path | None:
        return None  # remote backend — downloads are streamed/presigned
