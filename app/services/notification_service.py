from sqlalchemy.orm import Session

from app.models import Notification, User
from app.repositories.misc_repository import NotificationRepository
from app.utils.exceptions import ForbiddenError, NotFoundError


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationRepository(db)

    def list_for_user(self, user: User) -> list[Notification]:
        return self.notifications.list_for_user(user.id)

    def mark_read(self, user: User, notification_id: int) -> Notification:
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        if notification.user_id != user.id:
            raise ForbiddenError()
        notification.is_read = True
        return notification

    def mark_all_read(self, user: User) -> None:
        self.notifications.mark_all_read(user.id)
