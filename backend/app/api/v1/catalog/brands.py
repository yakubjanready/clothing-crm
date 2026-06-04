from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.brand import Brand
from app.models.user import User
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate
from app.services.audit import diff_attrs, log_activity
from app.services.catalog import slugify
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/brands")
ENTITY = "brand"


def _base(include_deleted: bool):
    stmt = select(Brand).order_by(Brand.name)
    if not include_deleted:
        stmt = stmt.where(Brand.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[BrandRead])
async def list_brands(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    country: str | None = Query(default=None, max_length=64),
    include_deleted: bool = Query(default=False),
) -> Page[BrandRead]:
    stmt = _base(include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Brand.name.ilike(like), Brand.slug.ilike(like)))
    if country:
        stmt = stmt.where(Brand.country == country)

    items, total, pages = await paginate(db, stmt, params)
    return Page[BrandRead](
        items=[BrandRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
) -> BrandRead:
    b = await db.get(Brand, brand_id)
    if b is None or b.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand topilmadi")
    return BrandRead.model_validate(b)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(
    body: BrandCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> BrandRead:
    data = body.model_dump()
    if not data.get("slug"):
        data["slug"] = slugify(data["name"])

    b = Brand(**data)
    db.add(b)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "name yoki slug band") from e

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=b.id, changes=data, request=request,
    )
    await db.commit()
    await db.refresh(b)
    return BrandRead.model_validate(b)


@router.patch("/{brand_id}", response_model=BrandRead)
async def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> BrandRead:
    b = await db.get(Brand, brand_id)
    if b is None or b.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {"name", "slug", "description", "country", "logo_url"}
    changes = diff_attrs(b, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(b, f, v)

    if changes:
        await log_activity(
            db, actor=actor, action=AuditAction.UPDATE,
            entity_type=ENTITY, entity_id=b.id, changes=changes, request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "name yoki slug band") from e
    await db.refresh(b)
    return BrandRead.model_validate(b)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_brand(
    brand_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:delete")),
) -> None:
    b = await db.get(Brand, brand_id)
    if b is None or b.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand topilmadi")
    b.soft_delete()
    await log_activity(
        db, actor=actor, action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY, entity_id=b.id, request=request,
    )
    await db.commit()


@router.post("/{brand_id}/restore", response_model=BrandRead)
async def restore_brand(
    brand_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> BrandRead:
    b = await db.get(Brand, brand_id)
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand topilmadi")
    if b.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Brand o'chirilmagan")
    b.restore()
    await log_activity(
        db, actor=actor, action=AuditAction.RESTORE,
        entity_type=ENTITY, entity_id=b.id, request=request,
    )
    await db.commit()
    await db.refresh(b)
    return BrandRead.model_validate(b)
