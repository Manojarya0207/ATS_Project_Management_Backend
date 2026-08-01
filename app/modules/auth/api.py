"""Auth API routes — thin controllers: validate, delegate, respond."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.ratelimit import auth_rate_limit, limiter
from app.modules.auth.dependencies import AuthServiceDep, CurrentUserDep
from app.modules.auth.schemas import (
    ChangePassword,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserRegister,
)
from app.modules.users.schemas import UserOut
from app.shared.responses import ApiResponse, ok

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[UserOut])
@limiter.limit(auth_rate_limit)
async def register(
    request: Request, payload: UserRegister, service: AuthServiceDep
) -> dict[str, Any]:
    user = await service.register(payload)
    return ok(UserOut.model_validate(user), message="Registration successful")


@router.post("/login", response_model=LoginResponse)
@limiter.limit(auth_rate_limit)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> dict[str, Any]:
    access, refresh, user = await service.login(form.username, form.password)
    return {
        **ok(
            {
                "access_token": access,
                "refresh_token": refresh,
                "token_type": "bearer",
                "user": UserOut.model_validate(user),
            },
            message="Login successful",
        ),
        # Duplicated top-level for Swagger UI's OAuth2 Authorize flow.
        "access_token": access,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=ApiResponse[TokenPair])
@limiter.limit(auth_rate_limit)
async def refresh(
    request: Request, payload: RefreshRequest, service: AuthServiceDep
) -> dict[str, Any]:
    access, new_refresh = await service.refresh(payload.refresh_token)
    return ok(
        {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"},
        message="Token refreshed",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, service: AuthServiceDep) -> None:
    await service.logout(payload.refresh_token)


@router.get("/me", response_model=ApiResponse[UserOut])
async def me(user: CurrentUserDep) -> dict[str, Any]:
    return ok(UserOut.model_validate(user))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePassword, user: CurrentUserDep, service: AuthServiceDep
) -> None:
    await service.change_password(user, payload)
