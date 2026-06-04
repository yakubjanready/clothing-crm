"""FastAPI dependency'lar — joriy foydalanuvchi va permission tekshiruvi."""
from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=True,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT access tokendan foydalanuvchini topadi (rollar+permissionlar bilan)."""
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Yaroqsiz token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sub yaroqsiz",
        ) from e

    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Foydalanuvchi topilmadi")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Foydalanuvchi faol emas")
    return user


PermDep = Callable[..., Coroutine[Any, Any, User]]


def require_permission(perm_code: str) -> PermDep:
    """Berilgan permission code'i talab qilinadigan dependency factory."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if perm_code not in user.permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission talab qilinadi: {perm_code}",
            )
        return user

    return _checker
