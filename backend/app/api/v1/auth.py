"""Auth endpointlari: login, refresh (rotation), logout, me, register.

Xavfsizlik:
- Brute-force lockout (Redis counter): N noto'g'ri urinish → M sek lockout
- Har bir auth eventi audit log'ga yoziladi (LOGIN, LOGOUT, login_failed)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
from app.models.activity_log import AuditAction
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.services.audit import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])


def _refresh_key(user_id: str, jti: str) -> str:
    return f"refresh:{user_id}:{jti}"


def _refresh_ttl_seconds() -> int:
    return settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def _login_fail_key(email: str) -> str:
    return f"loginfail:{email.lower()}"


def _login_lock_key(email: str) -> str:
    return f"loginlock:{email.lower()}"


# ---- POST /auth/login ----


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenPair:
    # 1) Brute-force lockout tekshiruvi
    lock_key = _login_lock_key(body.email)
    if await redis.exists(lock_key):
        ttl = await redis.ttl(lock_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Juda ko'p urinishlar — {ttl} sekunddan keyin urinib ko'ring",
            headers={"Retry-After": str(ttl)},
        )

    # 2) Foydalanuvchini topish + parolni tekshirish
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
    is_invalid = (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.hashed_password)
    )

    if is_invalid:
        # 3a) Xato urinishni counter'ga qo'shish
        fail_key = _login_fail_key(body.email)
        fails = await redis.incr(fail_key)
        if fails == 1:
            await redis.expire(fail_key, settings.LOGIN_FAIL_WINDOW_SECONDS)
        if fails >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            await redis.set(lock_key, "1", ex=settings.LOGIN_LOCKOUT_SECONDS)
            await redis.delete(fail_key)
        # 3b) Audit (faqat mavjud user uchun — email enumeration'ni kamaytirish)
        if user is not None:
            await log_activity(
                db,
                actor=user,
                action="login_failed",
                entity_type="user",
                entity_id=user.id,
                changes={"attempt": fails},
                request=request,
            )
            await db.commit()
        raise invalid

    # 4) Muvaffaqiyat — counter'ni o'chirish + tokenlar + audit
    await redis.delete(_login_fail_key(body.email), lock_key)

    assert user is not None  # type narrowing (yuqorida is_invalid bo'sh)
    access_token, _, _ = create_access_token(str(user.id))
    refresh_token, rjti, _ = create_refresh_token(str(user.id))
    await redis.set(_refresh_key(str(user.id), rjti), "1", ex=_refresh_ttl_seconds())

    await log_activity(
        db,
        actor=user,
        action=AuditAction.LOGIN,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    await db.commit()

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
    await redis.set(_refresh_key(user_id, new_jti), "1", ex=_refresh_ttl_seconds())
    return TokenPair(access_token=access_token, refresh_token=new_refresh)


# ---- POST /auth/logout ----


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Response:
    """Foydalanuvchining barcha refresh tokenlarini bekor qiladi + audit log."""
    pattern = _refresh_key(str(user.id), "*")
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break
    await log_activity(
        db,
        actor=user,
        action=AuditAction.LOGOUT,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
            select(Role).where(Role.id.in_(body.role_ids)).options(selectinload(Role.permissions))
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
