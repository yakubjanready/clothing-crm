from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.invoice import InvoiceRead
from app.schemas.order import (
    CancelRequest,
    OrderCreate,
    OrderRead,
    OrderUpdate,
)
from app.schemas.payment import PaymentCreate, PaymentRead
from app.services.audit import log_activity
from app.services.customer import CreditLimitExceededError
from app.services.order import (
    InsufficientStockError,
    InvalidMovementError,
    InvalidOrderTransitionError,
    OrderValidationError,
    build_draft_order,
    cancel_order,
    confirm_order,
    create_invoice,
    pay_order,
    replace_items,
    ship_order,
)
from app.tasks.celery_app import celery_app
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/orders")
ENTITY = "order"


def _raise_service_error(e: Exception) -> None:
    if isinstance(e, InsufficientStockError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if isinstance(e, CreditLimitExceededError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if isinstance(e, (InvalidOrderTransitionError, InvalidMovementError, OrderValidationError)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    raise e


async def _get_order_or_404(db: AsyncSession, order_id: uuid.UUID) -> Order:
    o = (
        await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.deleted_at.is_(None))
            .options(selectinload(Order.items))
        )
    ).scalar_one_or_none()
    if o is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order topilmadi")
    return o


async def _reload_with_items(db: AsyncSession, order_id: uuid.UUID) -> Order:
    """Yangi yaratilgan/o'zgartirilgan order'ni eager-loaded relationship bilan
    qayta yuklaydi — Pydantic serializatsiyasida lazy IO bo'lmasligi uchun
    (yangi obyektlarda `lazy=selectin` strategiyasi ishlamaydi)."""
    return (
        await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
    ).scalar_one()


# ---- CRUD ----

@router.get("", response_model=Page[OrderRead])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("order:read")),
    params: PageParams = Depends(page_params),
    status_: OrderStatus | None = Query(default=None, alias="status"),
    customer_id: uuid.UUID | None = Query(default=None),
    warehouse_id: uuid.UUID | None = Query(default=None),
    manager_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=64),
    include_deleted: bool = Query(default=False),
) -> Page[OrderRead]:
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    if not include_deleted:
        stmt = stmt.where(Order.deleted_at.is_(None))
    if status_ is not None:
        stmt = stmt.where(Order.status == status_)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if warehouse_id is not None:
        stmt = stmt.where(Order.warehouse_id == warehouse_id)
    if manager_id is not None:
        stmt = stmt.where(Order.manager_id == manager_id)
    if search:
        stmt = stmt.where(Order.number.ilike(f"%{search}%"))

    items, total, pages = await paginate(db, stmt, params)
    return Page[OrderRead](
        items=[OrderRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("order:read")),
) -> OrderRead:
    o = await _get_order_or_404(db, order_id)
    return OrderRead.model_validate(o)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> OrderRead:
    try:
        order = await build_draft_order(
            db,
            customer_id=body.customer_id,
            warehouse_id=body.warehouse_id,
            items_data=[i.model_dump() for i in body.items],
            discount=body.discount,
            notes=body.notes,
            manager_id=body.manager_id or actor.id,
        )
    except OrderValidationError as e:
        await db.rollback()
        _raise_service_error(e)

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=order.id,
        changes={"number": order.number, "total": str(order.total)},
        request=request,
    )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Order number band") from e
    fresh = await _reload_with_items(db, order.id)
    return OrderRead.model_validate(fresh)


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: uuid.UUID,
    body: OrderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> OrderRead:
    o = await _get_order_or_404(db, order_id)
    if o.status != OrderStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Faqat DRAFT tahrirlanadi")

    patch = body.model_dump(exclude_unset=True)
    if "items" in patch and patch["items"] is not None:
        try:
            await replace_items(db, order=o, items_data=patch["items"], discount=patch.get("discount"))
        except (OrderValidationError, InvalidOrderTransitionError) as e:
            await db.rollback()
            _raise_service_error(e)
    elif "discount" in patch and patch["discount"] is not None:
        o.discount = patch["discount"]
        from app.services.order import _recalculate_totals
        _recalculate_totals(o)
    for f in ("notes", "manager_id"):
        if f in patch:
            setattr(o, f, patch[f])

    await log_activity(
        db, actor=actor, action=AuditAction.UPDATE,
        entity_type=ENTITY, entity_id=o.id,
        changes={"keys": list(patch.keys())},
        request=request,
    )
    await db.commit()
    fresh = await _reload_with_items(db, o.id)
    return OrderRead.model_validate(fresh)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_order(
    order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> None:
    o = await _get_order_or_404(db, order_id)
    if o.status != OrderStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Faqat DRAFT o'chiriladi")
    o.soft_delete()
    await log_activity(
        db, actor=actor, action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY, entity_id=o.id, request=request,
    )
    await db.commit()


# ---- State actions ----

@router.post("/{order_id}/confirm", response_model=OrderRead)
async def confirm(
    order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:approve")),
) -> OrderRead:
    o = await _get_order_or_404(db, order_id)
    try:
        await confirm_order(db, order=o, actor=actor)
    except Exception as e:
        await db.rollback()
        _raise_service_error(e)
    await log_activity(
        db, actor=actor, action=AuditAction.UPDATE,
        entity_type=ENTITY, entity_id=o.id,
        changes={"transition": f"draft->confirmed", "total": str(o.total)},
        request=request,
    )
    await db.commit()
    fresh = await _reload_with_items(db, o.id)
    return OrderRead.model_validate(fresh)


@router.post("/{order_id}/pay", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def pay(
    order_id: uuid.UUID,
    body: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> PaymentRead:
    o = await _get_order_or_404(db, order_id)
    try:
        order, payment = await pay_order(
            db, order=o, amount=body.amount, method=body.method,
            actor=actor, notes=body.notes,
        )
    except Exception as e:
        await db.rollback()
        _raise_service_error(e)
    await log_activity(
        db, actor=actor, action=AuditAction.UPDATE,
        entity_type=ENTITY, entity_id=order.id,
        changes={"payment_amount": str(body.amount), "new_status": order.status},
        request=request,
    )
    await db.commit()
    await db.refresh(payment)
    return PaymentRead.model_validate(payment)


@router.post("/{order_id}/ship", response_model=OrderRead)
async def ship(
    order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> OrderRead:
    o = await _get_order_or_404(db, order_id)
    try:
        await ship_order(db, order=o, actor=actor)
    except Exception as e:
        await db.rollback()
        _raise_service_error(e)
    await log_activity(
        db, actor=actor, action=AuditAction.UPDATE,
        entity_type=ENTITY, entity_id=o.id,
        changes={"transition": f"->{o.status}"},
        request=request,
    )
    await db.commit()
    fresh = await _reload_with_items(db, o.id)
    return OrderRead.model_validate(fresh)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel(
    order_id: uuid.UUID,
    body: CancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> OrderRead:
    o = await _get_order_or_404(db, order_id)
    try:
        await cancel_order(db, order=o, actor=actor, reason=body.reason)
    except Exception as e:
        await db.rollback()
        _raise_service_error(e)
    await log_activity(
        db, actor=actor, action=AuditAction.UPDATE,
        entity_type=ENTITY, entity_id=o.id,
        changes={"transition": "->cancelled", "reason": body.reason},
        request=request,
    )
    await db.commit()
    fresh = await _reload_with_items(db, o.id)
    return OrderRead.model_validate(fresh)


# ---- Invoice yaratish ----

@router.post(
    "/{order_id}/invoices",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice_for_order(
    order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("order:write")),
) -> InvoiceRead:
    o = await _get_order_or_404(db, order_id)
    try:
        inv = await create_invoice(db, order=o)
    except Exception as e:
        await db.rollback()
        _raise_service_error(e)
    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type="invoice", entity_id=inv.id,
        changes={"order_number": o.number, "total": str(inv.total)},
        request=request,
    )
    await db.commit()
    await db.refresh(inv)

    # Celery PDF task (broker bo'lmasa silently — invoice yozuvi qoladi)
    try:
        celery_app.send_task("generate_invoice_pdf", args=[str(inv.id)])
    except Exception:  # noqa: BLE001
        pass

    return InvoiceRead.model_validate(inv)
