from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas.product_variant import (
    VariantCreate,
    VariantMatrixRequest,
    VariantMatrixResponse,
    VariantRead,
    VariantUpdate,
)
from app.services.audit import diff_attrs, log_activity
from app.services.catalog import build_variant_sku

router = APIRouter(prefix="/products/{product_id}/variants")
ENTITY = "product_variant"


async def _get_product_or_404(db: AsyncSession, product_id: uuid.UUID) -> Product:
    p = await db.get(Product, product_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    return p


@router.get("", response_model=list[VariantRead])
async def list_variants(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
) -> list[VariantRead]:
    await _get_product_or_404(db, product_id)
    rows = (
        (
            await db.execute(
                select(ProductVariant)
                .where(
                    ProductVariant.product_id == product_id,
                    ProductVariant.deleted_at.is_(None),
                )
                .order_by(ProductVariant.size, ProductVariant.color)
            )
        )
        .scalars()
        .all()
    )
    return [VariantRead.model_validate(r) for r in rows]


@router.post("", response_model=VariantRead, status_code=status.HTTP_201_CREATED)
async def create_variant(
    product_id: uuid.UUID,
    body: VariantCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> VariantRead:
    product = await _get_product_or_404(db, product_id)

    sku = build_variant_sku(product.sku_prefix, body.size, body.color)
    variant = ProductVariant(
        product_id=product.id,
        sku=sku,
        **body.model_dump(),
    )
    db.add(variant)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Variant (size, color) yoki SKU allaqachon mavjud",
        ) from e

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=variant.id,
        changes={**body.model_dump(), "sku": sku, "product_id": str(product.id)},
        request=request,
    )
    await db.commit()
    await db.refresh(variant)
    return VariantRead.model_validate(variant)


@router.post(
    "/matrix",
    response_model=VariantMatrixResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variant_matrix(
    product_id: uuid.UUID,
    body: VariantMatrixRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> VariantMatrixResponse:
    """size × color matritsasi — har bir kombinatsiya uchun variant yaratadi.
    Mavjudlari `skipped_existing` ichida qaytariladi."""
    product = await _get_product_or_404(db, product_id)

    existing_pairs = {
        (v.size, v.color)
        for v in (
            await db.execute(
                select(ProductVariant).where(
                    ProductVariant.product_id == product.id,
                    ProductVariant.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    }

    created: list[ProductVariant] = []
    skipped: list[dict[str, str]] = []
    for size in body.sizes:
        for color in body.colors:
            if (size, color.name) in existing_pairs:
                skipped.append({"size": size, "color": color.name})
                continue
            v = ProductVariant(
                product_id=product.id,
                sku=build_variant_sku(product.sku_prefix, size, color.name),
                size=size,
                color=color.name,
                color_hex=color.hex,
                wholesale_price=body.wholesale_price,
                retail_price=body.retail_price,
                is_active=body.is_active,
            )
            db.add(v)
            created.append(v)

    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU yoki size/color takrorlanishi") from e

    for v in created:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.CREATE,
            entity_type=ENTITY,
            entity_id=v.id,
            changes={
                "product_id": str(product.id),
                "sku": v.sku,
                "size": v.size,
                "color": v.color,
                "wholesale_price": str(v.wholesale_price),
                "retail_price": str(v.retail_price),
                "source": "matrix",
            },
            request=request,
        )

    await db.commit()
    for v in created:
        await db.refresh(v)

    return VariantMatrixResponse(
        created=[VariantRead.model_validate(v) for v in created],
        skipped_existing=skipped,
    )


@router.patch("/{variant_id}", response_model=VariantRead)
async def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    body: VariantUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:write")),
) -> VariantRead:
    product = await _get_product_or_404(db, product_id)
    variant = await db.get(ProductVariant, variant_id)
    if variant is None or variant.deleted_at is not None or variant.product_id != product.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {
        "size",
        "color",
        "color_hex",
        "wholesale_price",
        "retail_price",
        "barcode",
        "image_url",
        "is_active",
    }
    changes = diff_attrs(variant, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(variant, f, v)

    # size/color o'zgarsa, SKU ni qayta hisoblaymiz
    if "size" in patch or "color" in patch:
        new_sku = build_variant_sku(product.sku_prefix, variant.size, variant.color)
        if new_sku != variant.sku:
            changes["sku"] = {"old": variant.sku, "new": new_sku}
            variant.sku = new_sku

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=variant.id,
            changes=changes,
            request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU yoki size/color band") from e
    await db.refresh(variant)
    return VariantRead.model_validate(variant)


@router.delete("/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("product:delete")),
) -> None:
    product = await _get_product_or_404(db, product_id)
    variant = await db.get(ProductVariant, variant_id)
    if variant is None or variant.deleted_at is not None or variant.product_id != product.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant topilmadi")

    variant.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=variant.id,
        request=request,
    )
    await db.commit()
