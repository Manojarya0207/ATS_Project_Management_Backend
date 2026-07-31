from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.user import UserCreate, UserOut, UserRoleUpdate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserOut], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    return UserService(db).list_users()


@router.post("/", response_model=UserOut, status_code=201, dependencies=[Depends(require_admin)])
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    return UserService(db).create_user(data)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserService(db).get_user(user, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserService(db).update_user(user, user_id, data)


@router.patch("/{user_id}/role", response_model=UserOut, dependencies=[Depends(require_admin)])
def update_role(user_id: int, data: UserRoleUpdate, db: Session = Depends(get_db)):
    return UserService(db).update_role(user_id, data.role)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    UserService(db).delete_user(admin, user_id)
