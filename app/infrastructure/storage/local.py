"""Local-disk storage backend (development / single-node deployments)."""

from __future__ import annotations

import uuid
from pathlib import Path

import anyio
from fastapi import UploadFile

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.exceptions import ValidationAppError
from app.infrastructure.storage import StoredFile

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class LocalStorage:
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _key_for(self, original_filename: str) -> str:
        suffix = Path(original_filename or "").suffix[:16]
        return f"{uuid.uuid4().hex}{suffix}"

    async def save(self, upload: UploadFile, *, max_size_bytes: int) -> StoredFile:
        key = self._key_for(upload.filename or "")
        target = self.root / key
        size = 0
        try:
            async with await anyio.open_file(target, "wb") as out:
                while chunk := await upload.read(_CHUNK_SIZE):
                    size += len(chunk)
                    if size > max_size_bytes:
                        raise ValidationAppError(
                            f"File exceeds maximum size of {max_size_bytes} bytes",
                            code=ErrorCode.file_too_large,
                            field="file",
                        )
                    await out.write(chunk)
        except ValidationAppError:
            target.unlink(missing_ok=True)
            raise
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return StoredFile(key=key, size_bytes=size)

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(lambda: (self.root / key).unlink(missing_ok=True))

    def local_path(self, key: str) -> Path | None:
        path = self.root / key
        return path if path.is_file() else None
