from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.id)))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_valid(self, token: str) -> RefreshToken | None:
        rt = self.db.scalar(select(RefreshToken).where(RefreshToken.token == token))
        if rt is None or rt.revoked:
            return None
        expires = rt.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return None
        return rt

    def create(self, rt: RefreshToken) -> RefreshToken:
        self.db.add(rt)
        self.db.flush()
        return rt

    def revoke(self, rt: RefreshToken) -> None:
        rt.revoked = True

    def revoke_all_for_user(self, user_id: int) -> None:
        for rt in self.db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        ):
            rt.revoked = True
