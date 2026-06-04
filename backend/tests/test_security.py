"""core/security.py — bcrypt va JWT testlari."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ---- bcrypt ----

def test_hash_and_verify_password_roundtrip() -> None:
    h = hash_password("Secret123!")
    assert h != "Secret123!"
    assert h.startswith(("$2a$", "$2b$", "$2y$"))
    assert verify_password("Secret123!", h) is True
    assert verify_password("WrongPass", h) is False


def test_verify_password_with_invalid_hash_returns_false() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_hash_password_is_salted() -> None:
    a = hash_password("same-input")
    b = hash_password("same-input")
    assert a != b
    assert verify_password("same-input", a) is True
    assert verify_password("same-input", b) is True


# ---- JWT ----

def test_access_token_roundtrip() -> None:
    sub = str(uuid.uuid4())
    token, jti, exp = create_access_token(sub)

    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == sub
    assert payload["type"] == "access"
    assert payload["jti"] == jti
    assert isinstance(payload["exp"], int)
    # ~15 daq atrofida muddati o'tishi kerak
    delta_min = (exp - datetime.now(timezone.utc)).total_seconds() / 60
    assert 14 < delta_min < 16


def test_refresh_token_roundtrip_and_longer_lifetime() -> None:
    sub = str(uuid.uuid4())
    token, jti, exp = create_refresh_token(sub)

    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == sub
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    delta_days = (exp - datetime.now(timezone.utc)).total_seconds() / 86400
    assert 6.9 < delta_days < 7.1


def test_decode_access_as_refresh_raises() -> None:
    token, _, _ = create_access_token("user-1")
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="refresh")


def test_decode_refresh_as_access_raises() -> None:
    token, _, _ = create_refresh_token("user-1")
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="access")


def test_decode_tampered_signature_raises() -> None:
    token, _, _ = create_access_token("user-1")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(InvalidTokenError):
        decode_token(tampered, expected_type="access")


def test_decode_expired_token_raises() -> None:
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "user-1",
        "type": "access",
        "iat": int((now - timedelta(hours=1)).timestamp()),
        "exp": int((now - timedelta(minutes=1)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        expired_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="access")


def test_jti_is_unique_per_token() -> None:
    sub = "user-1"
    _, jti1, _ = create_access_token(sub)
    time.sleep(0.001)
    _, jti2, _ = create_access_token(sub)
    assert jti1 != jti2
