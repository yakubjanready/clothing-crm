"""/users — foydalanuvchilarni boshqarish (admin).

CRUD: list, get, patch (full_name/is_active/roles), soft-delete, parol reset.
Yaratish /auth/register orqali (mavjud) — RBAC user:write.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.role import Role
from app.models.user import User
from app.schemas.user import PasswordReset, UserListItem, UserRead, UserUpdate
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/users", tags=["users"])
ENTITY = "user"


def _base_select(include_deleted: bool = False):
    stmt = select(User).options(selectinload(User.roles)).order_by(User.full_name)
    if not include_deleted:
        stmt = stmt.where(User.deleted_at.is_(None))
    return stmt


async def _load_roles(db: AsyncSession, role_ids: list[uuid.UUID]) -> list[Role]:
    if not role_ids:
        return []
    result = await db.execute(
        select(Role).where(Role.id.in_(role_ids)).options(selectinload(Role.permissions))
    )
    roles = list(result.scalars())
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ba'zi role_ids topilmadi")
    return roles


# ---- GET /users ----


@router.get("", response_model=Page[UserListItem])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    role_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> Page[UserListItem]:
    stmt = _base_select(include_deleted=include_deleted)

    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if role_id is not None:
        stmt = stmt.where(User.roles.any(Role.id == role_id))

    items, total, pages = await paginate(db, stmt, params)
    return Page[UserListItem](
        items=[UserListItem.model_validate(u) for u in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


# ---- GET /users/{id} ----


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:read")),
) -> UserRead:
    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")
    return UserRead.model_validate(user)


# ---- PATCH /users/{id} ----


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("user:write")),
) -> UserRead:
    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")

    patch = body.model_dump(exclude_unset=True)

    # O'zini deaktiv qila olmaydi (admin o'zini bloklab qo'ymasligi uchun)
    if patch.get("is_active") is False and user.id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "O'zingizni deaktiv qila olmaysiz",
        )

    allowed = {"full_name", "is_active"}
    changes = diff_attrs(user, patch, allowed)
    for field, val in patch.items():
        if field in allowed:
            setattr(user, field, val)

    if "role_ids" in patch:
        # O'zining rollarini kamaytirib admin huquqini yo'qotmasligi uchun
        if user.id == actor.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "O'zingizning rollaringizni o'zgartira olmaysiz",
            )
        new_roles = await _load_roles(db, list(patch["role_ids"]))
        old_ids = sorted(str(r.id) for r in user.roles)
        new_ids = sorted(str(r.id) for r in new_roles)
        if old_ids != new_ids:
            changes["role_ids"] = {"old": old_ids, "new": new_ids}
        user.roles = new_roles

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=user.id,
            changes=changes,
            request=request,
        )
    await db.commit()
    await db.refresh(user, attribute_names=["roles"])
    return UserRead.model_validate(user)


# ---- DELETE /users/{id} (soft) ----


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("user:delete")),
) -> None:
    if user_id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "O'zingizni o'chira olmaysiz",
        )
    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")

    user.soft_delete()
    user.is_active = False
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=user.id,
        request=request,
    )
    await db.commit()


# ---- POST /users/{id}/restore ----


@router.post("/{user_id}/restore", response_model=UserRead)
async def restore_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("user:write")),
) -> UserRead:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")
    if user.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Foydalanuvchi o'chirilmagan")

    user.restore()
    user.is_active = True
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.RESTORE,
        entity_type=ENTITY,
        entity_id=user.id,
        request=request,
    )
    await db.commit()
    await db.refresh(user, attribute_names=["roles"])
    return UserRead.model_validate(user)


# ---- POST /users/{id}/reset-password ----


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("user:write")),
) -> None:
    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foydalanuvchi topilmadi")

    user.hashed_password = hash_password(body.password)
    await log_activity(
        db,
        actor=actor,
        action="password_reset",
        entity_type=ENTITY,
        entity_id=user.id,
        request=request,
    )
    await db.commit()


# ---- GET /users/me/permissions — joriy foydalanuvchining permission code'lari ----


@router.get("/me/permissions", response_model=list[str])
async def my_permissions(user: User = Depends(get_current_user)) -> list[str]:
    return sorted(user.permission_codes)
