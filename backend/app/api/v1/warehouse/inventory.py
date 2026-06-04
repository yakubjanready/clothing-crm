from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.inventory import Inventory, InventoryItem, InventoryStatus
from app.models.stock import Stock
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.inventory import (
    InventoryCreate,
    InventoryFinalizeResponse,
    InventoryItemCount,
    InventoryRead,
)
from app.services.stock import InsufficientStockError, adjust_stock
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/inventory")


@router.get("", response_model=Page[InventoryRead])
async def list_inventories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
    params: PageParams = Depends(page_params),
    warehouse_id: uuid.UUID | None = Query(default=None),
    status_: InventoryStatus | None = Query(default=None, alias="status"),
) -> Page[InventoryRead]:
    stmt = (
        select(Inventory)
        .options(selectinload(Inventory.items))
        .order_by(Inventory.created_at.desc())
    )
    if warehouse_id is not None:
        stmt = stmt.where(Inventory.warehouse_id == warehouse_id)
    if status_ is not None:
        stmt = stmt.where(Inventory.status == status_)

    items, total, pages = await paginate(db, stmt, params)
    return Page[InventoryRead](
        items=[InventoryRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{inventory_id}", response_model=InventoryRead)
async def get_inventory(
    inventory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
) -> InventoryRead:
    inv = (
        await db.execute(
            select(Inventory)
            .where(Inventory.id == inventory_id)
            .options(selectinload(Inventory.items))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inventarizatsiya topilmadi")
    return InventoryRead.model_validate(inv)


@router.post("", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
async def start_inventory(
    body: InventoryCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> InventoryRead:
    wh = await db.get(Warehouse, body.warehouse_id)
    if wh is None or wh.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "warehouse_id topilmadi")

    inv = Inventory(
        warehouse_id=body.warehouse_id,
        actor_id=actor.id,
        status=InventoryStatus.IN_PROGRESS,
        notes=body.notes,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv, attribute_names=["items"])
    return InventoryRead.model_validate(inv)


@router.post(
    "/{inventory_id}/items",
    response_model=InventoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def count_item(
    inventory_id: uuid.UUID,
    body: InventoryItemCount,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:write")),
) -> InventoryRead:
    inv = (
        await db.execute(
            select(Inventory)
            .where(Inventory.id == inventory_id)
            .options(selectinload(Inventory.items))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inventarizatsiya topilmadi")
    if inv.status != InventoryStatus.IN_PROGRESS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Sessiya holati {inv.status} — count qabul qilinmaydi",
        )

    expected = 0
    stock = (
        await db.execute(
            select(Stock).where(
                Stock.warehouse_id == inv.warehouse_id,
                Stock.variant_id == body.variant_id,
            )
        )
    ).scalar_one_or_none()
    if stock is not None:
        expected = stock.quantity

    existing = next((it for it in inv.items if it.variant_id == body.variant_id), None)
    if existing is None:
        item = InventoryItem(
            inventory_id=inv.id,
            variant_id=body.variant_id,
            expected_quantity=expected,
            counted_quantity=body.counted_quantity,
        )
        db.add(item)
    else:
        existing.counted_quantity = body.counted_quantity
        existing.expected_quantity = expected

    await db.commit()
    await db.refresh(inv, attribute_names=["items"])
    return InventoryRead.model_validate(inv)


@router.post("/{inventory_id}/finalize", response_model=InventoryFinalizeResponse)
async def finalize_inventory(
    inventory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> InventoryFinalizeResponse:
    inv = (
        await db.execute(
            select(Inventory)
            .where(Inventory.id == inventory_id)
            .options(selectinload(Inventory.items))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inventarizatsiya topilmadi")
    if inv.status != InventoryStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Holat {inv.status}")

    adjustments = 0
    try:
        for item in inv.items:
            delta = item.counted_quantity - item.expected_quantity
            if delta == 0:
                continue
            await adjust_stock(
                db,
                variant_id=item.variant_id,
                warehouse_id=inv.warehouse_id,
                delta=delta,
                actor=actor,
                reason=f"inventory {inv.id} finalize",
                reference_type="inventory",
                reference_id=inv.id,
            )
            adjustments += 1
    except InsufficientStockError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e

    inv.status = InventoryStatus.COMPLETED
    inv.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return InventoryFinalizeResponse(
        inventory_id=inv.id, adjustments=adjustments, status=inv.status
    )


@router.post("/{inventory_id}/cancel", response_model=InventoryRead)
async def cancel_inventory(
    inventory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:write")),
) -> InventoryRead:
    inv = (
        await db.execute(
            select(Inventory)
            .where(Inventory.id == inventory_id)
            .options(selectinload(Inventory.items))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inventarizatsiya topilmadi")
    if inv.status != InventoryStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Holat {inv.status}")
    inv.status = InventoryStatus.CANCELLED
    inv.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(inv, attribute_names=["items"])
    return InventoryRead.model_validate(inv)
