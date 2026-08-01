"""File attachment business logic — storage-backend agnostic."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.infrastructure.storage import StorageBackend
from app.modules.tasks.models import FileAttachment
from app.modules.tasks.repository import FileRepository
from app.modules.users.models import User


class FileService:
    def __init__(self, db: AsyncSession, storage: StorageBackend, settings: Settings) -> None:
        self.db = db
        self.storage = storage
        self.settings = settings
        self.files = FileRepository(db)

    async def list_for_task(self, task_id: uuid.UUID) -> list[FileAttachment]:
        return await self.files.list_for_task(task_id)

    async def upload(self, task_id: uuid.UUID, upload: UploadFile, actor: User) -> FileAttachment:
        stored = await self.storage.save(upload, max_size_bytes=self.settings.max_upload_size_bytes)
        attachment = await self.files.add(
            FileAttachment(
                task_id=task_id,
                uploaded_by=actor.id,
                original_filename=upload.filename or "unnamed",
                stored_filename=stored.key,
                content_type=upload.content_type,
                size_bytes=stored.size_bytes,
            )
        )
        loaded = await self.files.get(attachment.id)
        assert loaded is not None
        return loaded

    async def get_attachment(self, file_id: uuid.UUID) -> FileAttachment:
        attachment = await self.files.get(file_id)
        if attachment is None:
            raise NotFoundError("File not found")
        return attachment

    def resolve_download_path(self, attachment: FileAttachment) -> Path:
        path = self.storage.local_path(attachment.stored_filename)
        if path is None:
            raise NotFoundError("File not found in storage")
        return path
