from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.models.user import User
from app.schemas.supplier import (
    SupplierBalance,
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
)
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/suppliers")
ENTITY = "supplier"


def _base(include_deleted: bool):
    stmt = select(Supplier).order_by(Supplier.name)
    if not include_deleted:
        stmt = stmt.where(Supplier.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[SupplierRead])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("purchase:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    has_debt: bool | None = Query(default=None),
    min_rating: int | None = Query(default=None, ge=0, le=5),
    is_active: bool | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> Page[SupplierRead]:
    stmt = _base(include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Supplier.name.ilike(like),
                Supplier.inn.ilike(like),
                Supplier.phone.ilike(like),
            )
        )
    if has_debt is True:
        stmt = stmt.where(Supplier.current_debt > 0)
    elif has_debt is False:
        stmt = stmt.where(Supplier.current_debt == 0)
    if min_rating is not None:
        stmt = stmt.where(Supplier.rating >= min_rating)
    if is_active is not None:
        stmt = stmt.where(Supplier.is_active == is_active)

    items, total, pages = await paginate(db, stmt, params)
    return Page[SupplierRead](
        items=[SupplierRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("purchase:read")),
) -> SupplierRead:
    s = await db.get(Supplier, supplier_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier topilmadi")
    return SupplierRead.model_validate(s)


@router.get("/{supplier_id}/balance", response_model=SupplierBalance)
async def get_balance(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("purchase:read")),
) -> SupplierBalance:
    s = await db.get(Supplier, supplier_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier topilmadi")

    base_q = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.supplier_id == supplier_id,
        PurchaseOrder.deleted_at.is_(None),
    )
    orders_total = (await db.execute(base_q)).scalar_one()
    orders_received = (
        await db.execute(base_q.where(PurchaseOrder.status == PurchaseOrderStatus.RECEIVED))
    ).scalar_one()
    orders_paid = (
        await db.execute(base_q.where(PurchaseOrder.status == PurchaseOrderStatus.PAID))
    ).scalar_one()

    total_purchased = (
        await db.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total), 0)).where(
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.status.in_([PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.PAID]),
            )
        )
    ).scalar_one()
    total_paid = (
        await db.execute(
            select(func.coalesce(func.sum(SupplierPayment.amount), 0))
            .join(PurchaseOrder, SupplierPayment.purchase_order_id == PurchaseOrder.id)
            .where(PurchaseOrder.supplier_id == supplier_id)
        )
    ).scalar_one()

    return SupplierBalance(
        supplier_id=s.id,
        name=s.name,
        current_debt=s.current_debt,
        rating=s.rating,
        orders_total=orders_total,
        orders_received=orders_received,
        orders_paid=orders_paid,
        total_purchased=Decimal(total_purchased),
        total_paid=Decimal(total_paid),
    )


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> SupplierRead:
    s = Supplier(**body.model_dump())
    db.add(s)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "name yoki INN band") from e

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=s.id,
        changes=body.model_dump(),
        request=request,
    )
    await db.commit()
    await db.refresh(s)
    return SupplierRead.model_validate(s)


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: uuid.UUID,
    body: SupplierUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> SupplierRead:
    s = await db.get(Supplier, supplier_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {
        "name",
        "inn",
        "phone",
        "email",
        "address",
        "contact_person",
        "rating",
        "notes",
        "is_active",
    }
    changes = diff_attrs(s, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(s, f, v)

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=s.id,
            changes=changes,
            request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "name yoki INN band") from e
    await db.refresh(s)
    return SupplierRead.model_validate(s)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_supplier(
    supplier_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("purchase:write")),
) -> None:
    s = await db.get(Supplier, supplier_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier topilmadi")
    s.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=s.id,
        request=request,
    )
    await db.commit()
