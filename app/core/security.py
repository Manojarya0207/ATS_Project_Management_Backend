"""Security primitives: password hashing, password policy, JWT access tokens,
and opaque refresh-token generation/hashing.

bcrypt is CPU-bound (~100ms per hash by design), so hashing/verification are
offloaded to a worker thread via ``anyio.to_thread`` to keep the event loop
responsive. Refresh tokens are opaque random strings stored **hashed** (SHA-256)
so a database leak does not expose usable tokens.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import timedelta
from typing import Any

import anyio.to_thread
import bcrypt
from jose import JWTError, jwt

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.exceptions import ValidationAppError
from app.shared.utils import utcnow

# --- Password hashing --------------------------------------------------------


def _hash_password_sync(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password_sync(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


async def hash_password(password: str) -> str:
    return await anyio.to_thread.run_sync(_hash_password_sync, password)


async def verify_password(password: str, hashed: str) -> bool:
    return await anyio.to_thread.run_sync(_verify_password_sync, password, hashed)


# --- Password policy ---------------------------------------------------------

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")


def enforce_password_policy(password: str, settings: Settings) -> None:
    """Raise :class:`ValidationAppError` when the password is too weak.

    Policy: length within configured bounds, at least one uppercase letter,
    one lowercase letter, and one digit.
    """
    problems: list[str] = []
    if len(password) < settings.password_min_length:
        problems.append(f"at least {settings.password_min_length} characters")
    if len(password) > settings.password_max_length:
        problems.append(f"at most {settings.password_max_length} characters")
    if not _UPPER.search(password):
        problems.append("an uppercase letter")
    if not _LOWER.search(password):
        problems.append("a lowercase letter")
    if not _DIGIT.search(password):
        problems.append("a digit")
    if problems:
        raise ValidationAppError(
            "Password must contain " + ", ".join(problems),
            code=ErrorCode.weak_password,
            field="password",
        )


# --- JWT access tokens -------------------------------------------------------


def create_access_token(user_id: uuid.UUID, role: str, settings: Settings) -> str:
    expire = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(utcnow().timestamp()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any] | None:
    """Return the payload for a valid access token, else ``None``."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


# --- Refresh tokens (opaque, hashed at rest) ---------------------------------


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
