"""Auth endpointlari: login, refresh (rotation), logout, me, register."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_permission
from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _refresh_key(user_id: str, jti: str) -> str:
    return f"refresh:{user_id}:{jti}"


def _refresh_ttl_seconds() -> int:
    return settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


# ---- POST /auth/login ----

@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenPair:
    stmt = (
        select(User)
        .where(User.email == body.email, User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email yoki parol noto'g'ri",
    )
    if user is None or not user.is_active:
        raise invalid
    if not verify_password(body.password, user.hashed_password):
        raise invalid

    access_token, _, _ = create_access_token(str(user.id))
    refresh_token, rjti, _ = create_refresh_token(str(user.id))

    await redis.set(
        _refresh_key(str(user.id), rjti), "1", ex=_refresh_ttl_seconds()
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


# ---- POST /auth/refresh (rotation) ----

@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    redis: Redis = Depends(get_redis),
) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Yaroqsiz refresh token: {e}",
        ) from e

    user_id = payload["sub"]
    old_jti = payload["jti"]
    old_key = _refresh_key(user_id, old_jti)

    if not await redis.exists(old_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token bekor qilingan",
        )

    # Rotation: eski jti'ni o'chiramiz, yangi juftlik beramiz
    await redis.delete(old_key)
    access_token, _, _ = create_access_token(user_id)
    new_refresh, new_jti, _ = create_refresh_token(user_id)
    await redis.set(
        _refresh_key(user_id, new_jti), "1", ex=_refresh_ttl_seconds()
    )
    return TokenPair(access_token=access_token, refresh_token=new_refresh)


# ---- POST /auth/logout ----

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> None:
    """Foydalanuvchining barcha refresh tokenlarini bekor qiladi."""
    pattern = _refresh_key(str(user.id), "*")
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break


# ---- GET /auth/me ----

@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


# ---- POST /auth/register (admin: user:write) ----

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_permission("user:write")),
) -> UserRead:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu email allaqachon ro'yxatdan o'tgan",
        )

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        is_active=True,
    )

    if body.role_ids:
        roles_result = await db.execute(
            select(Role)
            .where(Role.id.in_(body.role_ids))
            .options(selectinload(Role.permissions))
        )
        roles = list(roles_result.scalars())
        if len(roles) != len(set(body.role_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ba'zi role_ids topilmadi",
            )
        user.roles = roles

    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["roles"])
    return UserRead.model_validate(user)
