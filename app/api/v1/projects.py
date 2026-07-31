from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.project import (
    MemberAdd,
    MemberOut,
    ProjectCreate,
    ProjectDetailOut,
    ProjectOut,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProjectService(db).list_projects(user)


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(
    data: ProjectCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    return ProjectService(db).create_project(admin, data)


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ProjectService(db).get_project(user, project_id)


@router.patch("/{project_id}", response_model=ProjectDetailOut)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ProjectService(db).update_project(admin, project_id, data)


@router.delete("/{project_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    ProjectService(db).delete_project(project_id)


@router.post(
    "/{project_id}/members",
    response_model=MemberOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def add_member(project_id: int, data: MemberAdd, db: Session = Depends(get_db)):
    return ProjectService(db).add_member(project_id, data)


@router.delete(
    "/{project_id}/members/{user_id}", status_code=204, dependencies=[Depends(require_admin)]
)
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db)):
    ProjectService(db).remove_member(project_id, user_id)
