import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Comment, FileAttachment, User, UserRole
from app.repositories.misc_repository import CommentRepository, FileRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.comment import CommentCreate, CommentUpdate
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationAppError


class CommentService:
    def __init__(self, db: Session):
        self.db = db
        self.comments = CommentRepository(db)
        self.tasks = TaskRepository(db)
        self.projects = ProjectRepository(db)

    def list_for_task(self, user: User, task_id: int) -> list[Comment]:
        self._require_task_access(user, task_id)
        return self.comments.list_for_task(task_id)

    def create(self, user: User, task_id: int, data: CommentCreate) -> Comment:
        self._require_task_access(user, task_id)
        comment = self.comments.create(
            Comment(task_id=task_id, user_id=user.id, content=data.content)
        )
        return self.comments.get(comment.id)

    def update(self, user: User, comment_id: int, data: CommentUpdate) -> Comment:
        comment = self._get_owned(user, comment_id)
        comment.content = data.content
        return comment

    def delete(self, user: User, comment_id: int) -> None:
        comment = self._get_owned(user, comment_id)
        self.comments.delete(comment)

    def _get_owned(self, user: User, comment_id: int) -> Comment:
        comment = self.comments.get(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        # Authors edit/delete their own comments; admins can moderate any.
        if user.role != UserRole.admin and comment.user_id != user.id:
            raise ForbiddenError("You can only modify your own comments")
        return comment

    def _require_task_access(self, user: User, task_id: int) -> None:
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if user.role == UserRole.admin:
            return
        if not self.projects.is_member(task.project_id, user.id):
            raise ForbiddenError("You are not a member of this project")


class FileStorage:
    """Local-disk storage. Swap this class for an S3 implementation later."""

    def __init__(self):
        self.base = Path(get_settings().upload_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, upload: UploadFile) -> tuple[str, int]:
        suffix = Path(upload.filename or "file").suffix[:16]
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        dest = self.base / stored_name
        size = 0
        max_size = get_settings().max_upload_size_bytes
        with dest.open("wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise ValidationAppError("File exceeds maximum allowed size")
                out.write(chunk)
        return stored_name, size

    def path_for(self, stored_filename: str) -> Path:
        return self.base / stored_filename


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.files = FileRepository(db)
        self.tasks = TaskRepository(db)
        self.projects = ProjectRepository(db)
        self.storage = FileStorage()

    def list_for_task(self, user: User, task_id: int) -> list[FileAttachment]:
        self._require_task_access(user, task_id)
        return self.files.list_for_task(task_id)

    def upload(self, user: User, task_id: int, upload: UploadFile) -> FileAttachment:
        self._require_task_access(user, task_id)
        stored_name, size = self.storage.save(upload)
        file = self.files.create(
            FileAttachment(
                task_id=task_id,
                uploaded_by=user.id,
                original_filename=upload.filename or "file",
                stored_filename=stored_name,
                content_type=upload.content_type,
                size_bytes=size,
            )
        )
        return self.files.get(file.id)

    def get_for_download(self, user: User, file_id: int) -> tuple[FileAttachment, Path]:
        file = self.files.get(file_id)
        if file is None:
            raise NotFoundError("File not found")
        self._require_task_access(user, file.task_id)
        path = self.storage.path_for(file.stored_filename)
        if not path.is_file():
            raise NotFoundError("Stored file is missing on disk")
        return file, path

    def _require_task_access(self, user: User, task_id: int) -> None:
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if user.role == UserRole.admin:
            return
        if not self.projects.is_member(task.project_id, user.id):
            raise ForbiddenError("You are not a member of this project")
