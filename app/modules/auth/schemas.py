"""Auth schemas.

``LoginResponse`` is the single deliberate envelope special-case: it duplicates
``access_token``/``token_type`` at the top level so Swagger UI's OAuth2
Authorize flow (which reads the raw response body) keeps working, while API
consumers read ``data.*`` like every other endpoint.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.schemas import UserOut
from app.shared.responses import ApiResponse


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class TokenPair(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginData(TokenPair):
    user: UserOut


class LoginResponse(ApiResponse[LoginData]):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
