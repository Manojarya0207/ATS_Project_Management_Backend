from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.models import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.utils.exceptions import ConflictError, ForbiddenError, NotFoundError


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def list_users(self) -> list[User]:
        return self.users.list_all()

    def get_user(self, requester: User, user_id: int) -> User:
        # Admin can fetch anyone; employees only themselves.
        if requester.role != UserRole.admin and requester.id != user_id:
            raise ForbiddenError()
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def create_user(self, data: UserCreate) -> User:
        if self.users.get_by_email(data.email):
            raise ConflictError("Email already registered")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        return self.users.create(user)

    def update_user(self, requester: User, user_id: int, data: UserUpdate) -> User:
        if requester.role != UserRole.admin and requester.id != user_id:
            raise ForbiddenError()
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if data.email is not None and data.email != user.email:
            if self.users.get_by_email(data.email):
                raise ConflictError("Email already registered")
            user.email = data.email
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.is_active is not None:
            # Only admins may activate/deactivate accounts.
            if requester.role != UserRole.admin:
                raise ForbiddenError()
            user.is_active = data.is_active
        return user

    def update_role(self, user_id: int, role: UserRole) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        user.role = role
        return user

    def delete_user(self, requester: User, user_id: int) -> None:
        if requester.id == user_id:
            raise ForbiddenError("You cannot delete your own account")
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        self.users.delete(user)
