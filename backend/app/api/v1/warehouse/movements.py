from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User
from app.schemas.stock import (
    MovementIssue,
    MovementReceive,
    MovementRelease,
    MovementReserve,
    MovementTransfer,
    StockMovementRead,
)
from app.services.stock import (
    InsufficientStockError,
    InvalidMovementError,
    issue_stock,
    receive_stock,
    release_reservation,
    reserve_stock,
    transfer_stock,
)
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/stock/movements")


def _raise(e: Exception) -> None:
    if isinstance(e, InsufficientStockError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if isinstance(e, InvalidMovementError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    raise e


@router.get("", response_model=Page[StockMovementRead])
async def list_movements(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
    params: PageParams = Depends(page_params),
    type_: MovementType | None = Query(default=None, alias="type"),
    variant_id: uuid.UUID | None = Query(default=None),
    warehouse_id: uuid.UUID | None = Query(
        default=None, description="from yoki to ombor"
    ),
    actor_id: uuid.UUID | None = Query(default=None),
) -> Page[StockMovementRead]:
    stmt = select(StockMovement).order_by(StockMovement.created_at.desc())
    if type_ is not None:
        stmt = stmt.where(StockMovement.type == type_)
    if variant_id is not None:
        stmt = stmt.where(StockMovement.variant_id == variant_id)
    if warehouse_id is not None:
        stmt = stmt.where(
            (StockMovement.from_warehouse_id == warehouse_id)
            | (StockMovement.to_warehouse_id == warehouse_id)
        )
    if actor_id is not None:
        stmt = stmt.where(StockMovement.actor_id == actor_id)

    items, total, pages = await paginate(db, stmt, params)
    return Page[StockMovementRead](
        items=[StockMovementRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.post("/receive", response_model=StockMovementRead, status_code=201)
async def post_receive(
    body: MovementReceive,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> StockMovementRead:
    try:
        mov = await receive_stock(
            db,
            variant_id=body.variant_id,
            to_warehouse_id=body.to_warehouse_id,
            quantity=body.quantity,
            actor=actor,
            reason=body.reason,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
        )
    except (InsufficientStockError, InvalidMovementError) as e:
        await db.rollback()
        _raise(e)
    await db.commit()
    await db.refresh(mov)
    return StockMovementRead.model_validate(mov)


@router.post("/issue", response_model=StockMovementRead, status_code=201)
async def post_issue(
    body: MovementIssue,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> StockMovementRead:
    try:
        mov = await issue_stock(
            db,
            variant_id=body.variant_id,
            from_warehouse_id=body.from_warehouse_id,
            quantity=body.quantity,
            actor=actor,
            reason=body.reason,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
        )
    except (InsufficientStockError, InvalidMovementError) as e:
        await db.rollback()
        _raise(e)
    await db.commit()
    await db.refresh(mov)
    return StockMovementRead.model_validate(mov)


@router.post("/transfer", response_model=StockMovementRead, status_code=201)
async def post_transfer(
    body: MovementTransfer,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> StockMovementRead:
    try:
        mov = await transfer_stock(
            db,
            variant_id=body.variant_id,
            from_warehouse_id=body.from_warehouse_id,
            to_warehouse_id=body.to_warehouse_id,
            quantity=body.quantity,
            actor=actor,
            reason=body.reason,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
        )
    except (InsufficientStockError, InvalidMovementError) as e:
        await db.rollback()
        _raise(e)
    await db.commit()
    await db.refresh(mov)
    return StockMovementRead.model_validate(mov)


@router.post("/reserve", response_model=StockMovementRead, status_code=201)
async def post_reserve(
    body: MovementReserve,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> StockMovementRead:
    try:
        mov = await reserve_stock(
            db,
            variant_id=body.variant_id,
            warehouse_id=body.warehouse_id,
            quantity=body.quantity,
            actor=actor,
            reason=body.reason,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
        )
    except (InsufficientStockError, InvalidMovementError) as e:
        await db.rollback()
        _raise(e)
    await db.commit()
    await db.refresh(mov)
    return StockMovementRead.model_validate(mov)


@router.post("/release", response_model=StockMovementRead, status_code=201)
async def post_release(
    body: MovementRelease,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> StockMovementRead:
    try:
        mov = await release_reservation(
            db,
            variant_id=body.variant_id,
            warehouse_id=body.warehouse_id,
            quantity=body.quantity,
            actor=actor,
            reason=body.reason,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
        )
    except InvalidMovementError as e:
        await db.rollback()
        _raise(e)
    await db.commit()
    await db.refresh(mov)
    return StockMovementRead.model_validate(mov)
