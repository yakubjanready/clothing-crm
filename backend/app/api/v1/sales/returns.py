from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.order import Order
from app.models.order_return import Return, ReturnStatus
from app.models.user import User
from app.schemas.order_return import ReturnCreate, ReturnRead
from app.services.audit import log_activity
from app.services.order import (
    InsufficientStockError,
    InvalidMovementError,
    InvalidOrderTransitionError,
    OrderValidationError,
    approve_return,
    create_return,
)
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/returns")


def _raise(e: Exception) -> None:
    if isinstance(e, InsufficientStockError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if isinstance(e, (InvalidOrderTransitionError, InvalidMovementError, OrderValidationError)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    raise e


@router.get("", response_model=Page[ReturnRead])
async def list_returns(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("order:read")),
    params: PageParams = Depends(page_params),
    order_id: uuid.UUID | None = Query(default=None),
    status_: ReturnStatus | None = Query(default=None, alias="status"),
) -> Page[ReturnRead]:
    stmt = (
        select(Return)
        .options(selectinload(Return.items))
        .order_by(Return.created_at.desc())
    )
    if order_id is not None:
        stmt = stmt.where(Return.order_id == order_id)
    if status_ is not None:
        stmt = stmt.where(Return.status == status_)

    items, total, pages = await paginate(db, stmt, params)
    return Page[ReturnRead](
        items=[ReturnRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{return_id}", response_model=ReturnRead)
async def get_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("order:read")),
) -> ReturnRead:
    ret = (
        await db.execute(
            select(Return)
            .where(Return.id == return_id)
            .options(selectinload(Return.items))
        )
    ).scalar_one_or_none()
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return topilmadi")
    return ReturnRead.model_validate(ret)


@router.post("", response_model=ReturnRead, status_code=status.HTTP_201_CREATED)
async def create_return_endpoint(
    body: ReturnCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> ReturnRead:
    order = (
        await db.execute(
            select(Order)
            .where(Order.id == body.order_id, Order.deleted_at.is_(None))
            .options(selectinload(Order.items))
        )
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order topilmadi")

    try:
        ret = await create_return(
            db, order=order,
            items_data=[i.model_dump() for i in body.items],
            actor=actor, reason=body.reason,
        )
    except Exception as e:
        await db.rollback()
        _raise(e)

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type="return", entity_id=ret.id,
        changes={"order_number": order.number, "total_refund": str(ret.total_refund)},
        request=request,
    )
    await db.commit()
    fresh = (
        await db.execute(
            select(Return)
            .where(Return.id == ret.id)
            .options(selectinload(Return.items))
        )
    ).scalar_one()
    return ReturnRead.model_validate(fresh)


@router.post("/{return_id}/approve", response_model=ReturnRead)
async def approve_return_endpoint(
    return_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:approve")),
) -> ReturnRead:
    ret = (
        await db.execute(
            select(Return)
            .where(Return.id == return_id)
            .options(selectinload(Return.items))
        )
    ).scalar_one_or_none()
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return topilmadi")

    try:
        await approve_return(db, ret=ret, actor=actor)
    except Exception as e:
        await db.rollback()
        _raise(e)

    await log_activity(
        db, actor=actor, action=AuditAction.UPDATE,
        entity_type="return", entity_id=ret.id,
        changes={"transition": "requested->approved", "refund": str(ret.total_refund)},
        request=request,
    )
    await db.commit()
    fresh = (
        await db.execute(
            select(Return)
            .where(Return.id == ret.id)
            .options(selectinload(Return.items))
        )
    ).scalar_one()
    return ReturnRead.model_validate(fresh)
