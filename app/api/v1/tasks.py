from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.task import KanbanBoard, TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/project/{project_id}", response_model=list[TaskOut])
def list_project_tasks(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return TaskService(db).list_for_project(user, project_id)


@router.get("/project/{project_id}/kanban", response_model=KanbanBoard)
def kanban_board(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return TaskService(db).kanban_board(user, project_id)


@router.post("/", response_model=TaskOut, status_code=201)
def create_task(
    data: TaskCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return TaskService(db).create_task(user, data)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TaskService(db).get_task(user, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TaskService(db).update_task(user, task_id, data)


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TaskService(db).update_status(user, task_id, data)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    TaskService(db).delete_task(user, task_id)
