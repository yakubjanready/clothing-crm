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
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.supplier import Supplier
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.purchase_order import (
    POCancelRequest,
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchaseOrderUpdate,
    SupplierPaymentCreate,
    SupplierPaymentRead,
)
from app.services.audit import log_activity
from app.services.purchase import (
    InvalidPurchaseTransitionError,
    PurchaseValidationError,
    build_draft_purchase,
    cancel_purchase,
    pay_supplier,
    receive_purchase,
    reload_with_items,
    replace_items,
)
from app.services.stock import InsufficientStockError, InvalidMovementError
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/purchase-orders")
ENTITY = "purchase_order"


def _raise(e: Exception) -> None:
    if isinstance(e, InsufficientStockError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if isinstance(
        e,
        (InvalidPurchaseTransitionError, PurchaseValidationError, InvalidMovementError),
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    raise e


async def _get_po_or_404(db: AsyncSession, po_id: uuid.UUID) -> PurchaseOrder:
    po = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
            .options(selectinload(PurchaseOrder.items))
        )
    ).scalar_one_or_none()
    if po is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order topilmadi")
    return po


# ---- CRUD ----


@router.get("", response_model=Page[PurchaseOrderRead])
async def list_purchase_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("purchase:read")),
    params: PageParams = Depends(page_params),
    status_: PurchaseOrderStatus | None = Query(default=None, alias="status"),
    supplier_id: uuid.UUID | None = Query(default=None),
    warehouse_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=64),
    include_deleted: bool = Query(default=False),
) -> Page[PurchaseOrderRead]:
    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .order_by(PurchaseOrder.created_at.desc())
    )
    if not include_deleted:
        stmt = stmt.where(PurchaseOrder.deleted_at.is_(None))
    if status_ is not None:
        stmt = stmt.where(PurchaseOrder.status == status_)
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if warehouse_id is not None:
        stmt = stmt.where(PurchaseOrder.warehouse_id == warehouse_id)
    if search:
        stmt = stmt.where(PurchaseOrder.number.ilike(f"%{search}%"))

    items, total, pages = await paginate(db, stmt, params)
    return Page[PurchaseOrderRead](
        items=[PurchaseOrderRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{po_id}", response_model=PurchaseOrderRead)
async def get_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("purchase:read")),
) -> PurchaseOrderRead:
    po = await _get_po_or_404(db, po_id)
    return PurchaseOrderRead.model_validate(po)


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> PurchaseOrderRead:
    # Avval supplier/warehouse mavjudligini tekshiramiz
    s = await db.get(Supplier, body.supplier_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "supplier_id topilmadi")
    w = await db.get(Warehouse, body.warehouse_id)
    if w is None or w.deleted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "warehouse_id topilmadi")

    try:
        po = await build_draft_purchase(
            db,
            supplier_id=body.supplier_id,
            warehouse_id=body.warehouse_id,
            items_data=[i.model_dump() for i in body.items],
            notes=body.notes,
            manager_id=body.manager_id or actor.id,
        )
    except PurchaseValidationError as e:
        await db.rollback()
        _raise(e)

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=po.id,
        changes={"number": po.number, "total": str(po.total)},
        request=request,
    )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "PO number band") from e
    fresh = await reload_with_items(db, po.id)
    return PurchaseOrderRead.model_validate(fresh)


@router.patch("/{po_id}", response_model=PurchaseOrderRead)
async def update_purchase_order(
    po_id: uuid.UUID,
    body: PurchaseOrderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> PurchaseOrderRead:
    po = await _get_po_or_404(db, po_id)
    if po.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Faqat DRAFT tahrirlanadi")

    patch = body.model_dump(exclude_unset=True)
    if "items" in patch and patch["items"] is not None:
        try:
            await replace_items(db, po=po, items_data=patch["items"])
        except (PurchaseValidationError, InvalidPurchaseTransitionError) as e:
            await db.rollback()
            _raise(e)
    for f in ("notes", "manager_id"):
        if f in patch:
            setattr(po, f, patch[f])

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type=ENTITY,
        entity_id=po.id,
        changes={"keys": list(patch.keys())},
        request=request,
    )
    await db.commit()
    fresh = await reload_with_items(db, po.id)
    return PurchaseOrderRead.model_validate(fresh)


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> None:
    po = await _get_po_or_404(db, po_id)
    if po.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Faqat DRAFT o'chiriladi")
    po.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=po.id,
        request=request,
    )
    await db.commit()


# ---- State actions ----


@router.post("/{po_id}/receive", response_model=PurchaseOrderRead)
async def receive(
    po_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:approve")),
) -> PurchaseOrderRead:
    po = await _get_po_or_404(db, po_id)
    try:
        await receive_purchase(db, po=po, actor=actor)
    except Exception as e:
        await db.rollback()
        _raise(e)
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type=ENTITY,
        entity_id=po.id,
        changes={"transition": "draft->received", "total": str(po.total)},
        request=request,
    )
    await db.commit()
    fresh = await reload_with_items(db, po.id)
    return PurchaseOrderRead.model_validate(fresh)


@router.post(
    "/{po_id}/pay", response_model=SupplierPaymentRead, status_code=status.HTTP_201_CREATED
)
async def pay(
    po_id: uuid.UUID,
    body: SupplierPaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:approve")),
) -> SupplierPaymentRead:
    po = await _get_po_or_404(db, po_id)
    try:
        po, payment = await pay_supplier(
            db,
            po=po,
            amount=body.amount,
            method=body.method,
            actor=actor,
            notes=body.notes,
        )
    except Exception as e:
        await db.rollback()
        _raise(e)
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type=ENTITY,
        entity_id=po.id,
        changes={"payment_amount": str(body.amount), "new_status": po.status},
        request=request,
    )
    await db.commit()
    await db.refresh(payment)
    return SupplierPaymentRead.model_validate(payment)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderRead)
async def cancel(
    po_id: uuid.UUID,
    body: POCancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> PurchaseOrderRead:
    po = await _get_po_or_404(db, po_id)
    try:
        await cancel_purchase(db, po=po, actor=actor, reason=body.reason)
    except Exception as e:
        await db.rollback()
        _raise(e)
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type=ENTITY,
        entity_id=po.id,
        changes={"transition": "->cancelled", "reason": body.reason},
        request=request,
    )
    await db.commit()
    fresh = await reload_with_items(db, po.id)
    return PurchaseOrderRead.model_validate(fresh)
