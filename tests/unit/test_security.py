"""Unit tests: password hashing/policy, JWT, refresh-token helpers."""

from __future__ import annotations

import uuid

import pytest
from app.core.exceptions import ValidationAppError
from app.core.security import (
    create_access_token,
    decode_access_token,
    enforce_password_policy,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

from tests.conftest import make_settings


async def test_password_hash_roundtrip():
    hashed = await hash_password("S3cure-pass")
    assert hashed != "S3cure-pass"
    assert await verify_password("S3cure-pass", hashed)
    assert not await verify_password("wrong", hashed)


async def test_verify_password_bad_hash_returns_false():
    assert not await verify_password("whatever", "not-a-bcrypt-hash")


@pytest.mark.parametrize(
    "password",
    ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere"],
)
def test_password_policy_rejects_weak(password):
    with pytest.raises(ValidationAppError):
        enforce_password_policy(password, make_settings())


def test_password_policy_accepts_strong():
    enforce_password_policy("Str0ngPassw0rd", make_settings())  # no raise


def test_jwt_roundtrip():
    settings = make_settings()
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "admin", settings)
    payload = decode_access_token(token, settings)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_jwt_rejects_wrong_secret():
    token = create_access_token(uuid.uuid4(), "admin", make_settings())
    other = make_settings(jwt_secret_key="a-completely-different-secret-key")
    assert decode_access_token(token, other) is None


def test_jwt_rejects_garbage():
    assert decode_access_token("garbage.token.here", make_settings()) is None


def test_refresh_token_hashing_is_deterministic_and_opaque():
    token = generate_refresh_token()
    assert len(token) > 50
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
