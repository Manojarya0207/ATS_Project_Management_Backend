from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.auth import LoginResponse, LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import ChangePassword, UserOut, UserRegister
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, request: Request, db: Session = Depends(get_db)):
    return AuthService(db).register(data)


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user, access, refresh = AuthService(db).login(form.username, form.password)
    return LoginResponse(access_token=access, refresh_token=refresh, user=user)


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    _, access, new_refresh = AuthService(db).refresh(data.refresh_token)
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
def logout(data: LogoutRequest, db: Session = Depends(get_db)):
    AuthService(db).logout(data.refresh_token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService(db).change_password(user, data)
