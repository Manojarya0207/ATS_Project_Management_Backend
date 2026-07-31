from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Comment, FileAttachment, Notification


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, comment_id: int) -> Comment | None:
        return self.db.scalar(
            select(Comment).options(selectinload(Comment.user)).where(Comment.id == comment_id)
        )

    def list_for_task(self, task_id: int) -> list[Comment]:
        return list(
            self.db.scalars(
                select(Comment)
                .options(selectinload(Comment.user))
                .where(Comment.task_id == task_id)
                .order_by(Comment.created_at)
            )
        )

    def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        self.db.flush()
        return comment

    def delete(self, comment: Comment) -> None:
        self.db.delete(comment)


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, file_id: int) -> FileAttachment | None:
        return self.db.scalar(
            select(FileAttachment)
            .options(selectinload(FileAttachment.uploader))
            .where(FileAttachment.id == file_id)
        )

    def list_for_task(self, task_id: int) -> list[FileAttachment]:
        return list(
            self.db.scalars(
                select(FileAttachment)
                .options(selectinload(FileAttachment.uploader))
                .where(FileAttachment.task_id == task_id)
                .order_by(FileAttachment.created_at.desc())
            )
        )

    def create(self, file: FileAttachment) -> FileAttachment:
        self.db.add(file)
        self.db.flush()
        return file


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, notification_id: int) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def list_for_user(self, user_id: int) -> list[Notification]:
        return list(
            self.db.scalars(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
            )
        )

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def mark_all_read(self, user_id: int) -> None:
        for n in self.db.scalars(
            select(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
        ):
            n.is_read = True
