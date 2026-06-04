from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.audit import diff_attrs, log_activity
from app.services.catalog import slugify
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/categories")
ENTITY = "category"


def _base(include_deleted: bool):
    stmt = select(Category).order_by(Category.name)
    if not include_deleted:
        stmt = stmt.where(Category.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[CategoryRead])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    parent_id: uuid.UUID | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> Page[CategoryRead]:
    stmt = _base(include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Category.name.ilike(like), Category.slug.ilike(like)))
    if parent_id is not None:
        stmt = stmt.where(Category.parent_id == parent_id)

    items, total, pages = await paginate(db, stmt, params)
    return Page[CategoryRead](
        items=[CategoryRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
) -> CategoryRead:
    cat = await db.get(Category, category_id)
    if cat is None or cat.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kategoriya topilmadi")
    return CategoryRead.model_validate(cat)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> CategoryRead:
    if body.parent_id is not None:
        parent = await db.get(Category, body.parent_id)
        if parent is None or parent.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id topilmadi")

    data = body.model_dump()
    if not data.get("slug"):
        data["slug"] = slugify(data["name"])
    cat = Category(**data)
    db.add(cat)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "slug band") from e

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=cat.id, changes=data, request=request,
    )
    await db.commit()
    await db.refresh(cat)
    return CategoryRead.model_validate(cat)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> CategoryRead:
    cat = await db.get(Category, category_id)
    if cat is None or cat.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kategoriya topilmadi")

    patch = body.model_dump(exclude_unset=True)
    if "parent_id" in patch and patch["parent_id"] is not None:
        if patch["parent_id"] == category_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id == id bo'la olmaydi")
        parent = await db.get(Category, patch["parent_id"])
        if parent is None or parent.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id topilmadi")

    allowed = {"name", "slug", "description", "image_url", "parent_id"}
    changes = diff_attrs(cat, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(cat, f, v)

    if changes:
        await log_activity(
            db, actor=actor, action=AuditAction.UPDATE,
            entity_type=ENTITY, entity_id=cat.id, changes=changes, request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "slug band") from e
    await db.refresh(cat)
    return CategoryRead.model_validate(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_category(
    category_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:delete")),
) -> None:
    cat = await db.get(Category, category_id)
    if cat is None or cat.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kategoriya topilmadi")
    cat.soft_delete()
    await log_activity(
        db, actor=actor, action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY, entity_id=cat.id, request=request,
    )
    await db.commit()


@router.post("/{category_id}/restore", response_model=CategoryRead)
async def restore_category(
    category_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> CategoryRead:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kategoriya topilmadi")
    if cat.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kategoriya o'chirilmagan")
    cat.restore()
    await log_activity(
        db, actor=actor, action=AuditAction.RESTORE,
        entity_type=ENTITY, entity_id=cat.id, request=request,
    )
    await db.commit()
    await db.refresh(cat)
    return CategoryRead.model_validate(cat)
