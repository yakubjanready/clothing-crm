from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.stock import Stock
from app.models.user import User
from app.schemas.stock import StockMinUpdate, StockRead
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/stock")


def _to_read(s: Stock) -> StockRead:
    return StockRead(
        id=s.id,
        warehouse_id=s.warehouse_id,
        variant_id=s.variant_id,
        quantity=s.quantity,
        reserved=s.reserved,
        min_quantity=s.min_quantity,
        available=s.quantity - s.reserved,
    )


@router.get("", response_model=Page[StockRead])
async def list_stock(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
    params: PageParams = Depends(page_params),
    warehouse_id: uuid.UUID | None = Query(default=None),
    variant_id: uuid.UUID | None = Query(default=None),
    low_only: bool = Query(default=False, description="Faqat available < min"),
) -> Page[StockRead]:
    stmt = select(Stock)
    if warehouse_id is not None:
        stmt = stmt.where(Stock.warehouse_id == warehouse_id)
    if variant_id is not None:
        stmt = stmt.where(Stock.variant_id == variant_id)
    if low_only:
        stmt = stmt.where(
            Stock.min_quantity > 0,
            (Stock.quantity - Stock.reserved) < Stock.min_quantity,
        )

    items, total, pages = await paginate(db, stmt, params)
    return Page[StockRead](
        items=[_to_read(s) for s in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{stock_id}", response_model=StockRead)
async def get_stock(
    stock_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
) -> StockRead:
    s = await db.get(Stock, stock_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock yozuvi topilmadi")
    return _to_read(s)


@router.patch("/{stock_id}/min", response_model=StockRead)
async def update_min_quantity(
    stock_id: uuid.UUID,
    body: StockMinUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:write")),
) -> StockRead:
    s = await db.get(Stock, stock_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock yozuvi topilmadi")
    s.min_quantity = body.min_quantity
    await db.commit()
    await db.refresh(s)
    return _to_read(s)
