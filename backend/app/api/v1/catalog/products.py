from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Gender, Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.audit import diff_attrs, log_activity
from app.services.catalog import generate_sku_prefix, slugify
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/products")
ENTITY = "product"


def _base(include_deleted: bool):
    stmt = select(Product).order_by(Product.name)
    if not include_deleted:
        stmt = stmt.where(Product.deleted_at.is_(None))
    return stmt


async def _ensure_refs(db: AsyncSession, category_id, brand_id) -> None:
    if category_id is not None:
        cat = await db.get(Category, category_id)
        if cat is None or cat.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "category_id topilmadi")
    if brand_id is not None:
        b = await db.get(Brand, brand_id)
        if b is None or b.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "brand_id topilmadi")


@router.get("", response_model=Page[ProductRead])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    category_id: uuid.UUID | None = Query(default=None),
    brand_id: uuid.UUID | None = Query(default=None),
    gender: Gender | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    include_deleted: bool = Query(default=False),
) -> Page[ProductRead]:
    stmt = _base(include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(like),
                Product.sku_prefix.ilike(like),
                Product.description.ilike(like),
            )
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if brand_id is not None:
        stmt = stmt.where(Product.brand_id == brand_id)
    if gender is not None:
        stmt = stmt.where(Product.gender == gender)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    if min_price is not None or max_price is not None:
        # narx variantlarda — products ichida hech bo'lmasa bitta variant shartni qondirsin
        sub = select(ProductVariant.product_id).where(ProductVariant.deleted_at.is_(None))
        if min_price is not None:
            sub = sub.where(ProductVariant.wholesale_price >= min_price)
        if max_price is not None:
            sub = sub.where(ProductVariant.wholesale_price <= max_price)
        stmt = stmt.where(Product.id.in_(sub))

    items, total, pages = await paginate(db, stmt, params)
    return Page[ProductRead](
        items=[ProductRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
) -> ProductRead:
    p = (
        await db.execute(
            select(Product).where(Product.id == product_id).options(selectinload(Product.variants))
        )
    ).scalar_one_or_none()
    if p is None or p.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    return ProductRead.model_validate(p)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> ProductRead:
    await _ensure_refs(db, body.category_id, body.brand_id)

    data = body.model_dump()
    if not data.get("slug"):
        data["slug"] = slugify(data["name"])
    if not data.get("sku_prefix"):
        data["sku_prefix"] = generate_sku_prefix(data["name"])

    p = Product(**data)
    db.add(p)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "slug yoki sku_prefix band") from e

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=p.id,
        changes=data,
        request=request,
    )
    await db.commit()
    await db.refresh(p)
    return ProductRead.model_validate(p)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> ProductRead:
    p = await db.get(Product, product_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")

    patch = body.model_dump(exclude_unset=True)
    await _ensure_refs(
        db,
        patch.get("category_id") if "category_id" in patch else None,
        patch.get("brand_id") if "brand_id" in patch else None,
    )

    allowed = {
        "name",
        "slug",
        "description",
        "material",
        "gender",
        "images",
        "is_active",
        "category_id",
        "brand_id",
    }
    changes = diff_attrs(p, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(p, f, v)

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=p.id,
            changes=changes,
            request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "slug band") from e
    await db.refresh(p)
    return ProductRead.model_validate(p)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_product(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:delete")),
) -> None:
    p = await db.get(Product, product_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    p.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=p.id,
        request=request,
    )
    await db.commit()


@router.post("/{product_id}/restore", response_model=ProductRead)
async def restore_product(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> ProductRead:
    p = await db.get(Product, product_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    if p.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mahsulot o'chirilmagan")
    p.restore()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.RESTORE,
        entity_type=ENTITY,
        entity_id=p.id,
        request=request,
    )
    await db.commit()
    await db.refresh(p)
    return ProductRead.model_validate(p)
