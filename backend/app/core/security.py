"""Parol xeshlash (bcrypt) va JWT (access/refresh) yordamchilari."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    """Yaroqsiz/muddati o'tgan/turi noto'g'ri JWT token."""


# ---- Parol ----


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---- JWT ----


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> tuple[str, str, datetime]:
    """Tokenni yaratadi va (jwt, jti, expires_at) qaytaradi."""
    now = datetime.now(UTC)
    expire = now + expires_delta
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti, expire


def create_access_token(subject: str) -> tuple[str, str, datetime]:
    return _create_token(subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    return _create_token(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        raise InvalidTokenError(str(e)) from e

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"expected {expected_type} token, got {payload.get('type')!r}")
    if "sub" not in payload or "jti" not in payload:
        raise InvalidTokenError("token missing required claims (sub, jti)")
    return payload
