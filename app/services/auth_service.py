from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    generate_refresh_token,
    refresh_token_expiry,
)
from app.auth.password import hash_password, verify_password
from app.models import RefreshToken, User, UserRole
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.user import ChangePassword, UserRegister
from app.utils.exceptions import ConflictError, UnauthorizedError


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)

    def register(self, data: UserRegister) -> User:
        if self.users.get_by_email(data.email):
            raise ConflictError("Email already registered")
        # Public registration always creates an employee.
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.employee,
        )
        return self.users.create(user)

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")
        return user, *self._issue_pair(user)

    def refresh(self, refresh_token: str) -> tuple[User, str, str]:
        rt = self.tokens.get_valid(refresh_token)
        if rt is None:
            raise UnauthorizedError("Invalid or expired refresh token")
        user = self.users.get(rt.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        # Rotation: revoke the old token, issue a fresh pair.
        self.tokens.revoke(rt)
        return user, *self._issue_pair(user)

    def logout(self, refresh_token: str) -> None:
        rt = self.tokens.get_valid(refresh_token)
        if rt is not None:
            self.tokens.revoke(rt)

    def change_password(self, user: User, data: ChangePassword) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        user.hashed_password = hash_password(data.new_password)
        # Invalidate all sessions on password change.
        self.tokens.revoke_all_for_user(user.id)

    def _issue_pair(self, user: User) -> tuple[str, str]:
        access = create_access_token(user.id, user.role.value)
        refresh = generate_refresh_token()
        self.tokens.create(
            RefreshToken(token=refresh, user_id=user.id, expires_at=refresh_token_expiry())
        )
        return access, refresh
