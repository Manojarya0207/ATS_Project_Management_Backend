"""File attachment API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import FileResponse

from app.core.dependencies import DbDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.tasks.dependencies import (
    AccessibleTaskDep,
    FileServiceDep,
    get_accessible_task,
)
from app.modules.tasks.schemas import FileOut
from app.shared.responses import ApiResponse, ok

router = APIRouter(tags=["Files"])


@router.get("/tasks/{task_id}/files", response_model=ApiResponse[list[FileOut]])
async def list_files(task: AccessibleTaskDep, service: FileServiceDep) -> dict[str, Any]:
    attachments = await service.list_for_task(task.id)
    return ok([FileOut.model_validate(f) for f in attachments])


@router.post(
    "/tasks/{task_id}/files",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[FileOut],
)
async def upload_file(
    task: AccessibleTaskDep,
    actor: CurrentUserDep,
    service: FileServiceDep,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    attachment = await service.upload(task.id, file, actor)
    return ok(FileOut.model_validate(attachment), message="File uploaded")


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: uuid.UUID, actor: CurrentUserDep, service: FileServiceDep, db: DbDep
) -> FileResponse:
    attachment = await service.get_attachment(file_id)
    await get_accessible_task(attachment.task_id, actor, db)  # project access check
    path = service.resolve_download_path(attachment)
    return FileResponse(
        path,
        filename=attachment.original_filename,
        media_type=attachment.content_type or "application/octet-stream",
    )
