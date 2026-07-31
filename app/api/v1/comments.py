from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.services.comment_file_service import CommentService

router = APIRouter(tags=["Comments"])


@router.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
def list_comments(
    task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return CommentService(db).list_for_task(user, task_id)


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    task_id: int,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CommentService(db).create(user, task_id, data)


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def update_comment(
    comment_id: int,
    data: CommentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CommentService(db).update(user, comment_id, data)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    CommentService(db).delete(user, comment_id)
