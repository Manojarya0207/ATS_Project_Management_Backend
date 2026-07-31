from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.notification import NotificationOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationOut])
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).list_for_user(user)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return NotificationService(db).mark_read(user, notification_id)


@router.post("/read-all", status_code=204)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    NotificationService(db).mark_all_read(user)
