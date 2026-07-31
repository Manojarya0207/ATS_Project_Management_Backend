from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.file import FileOut
from app.services.comment_file_service import FileService

router = APIRouter(tags=["Files"])


@router.get("/tasks/{task_id}/files", response_model=list[FileOut])
def list_files(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FileService(db).list_for_task(user, task_id)


@router.post("/tasks/{task_id}/files", response_model=FileOut, status_code=201)
def upload_file(
    task_id: int,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return FileService(db).upload(user, task_id, file)


@router.get("/files/{file_id}/download")
def download_file(
    file_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    attachment, path = FileService(db).get_for_download(user, file_id)
    return FileResponse(
        path,
        filename=attachment.original_filename,
        media_type=attachment.content_type or "application/octet-stream",
    )
