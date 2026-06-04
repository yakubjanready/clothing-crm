from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.customer import Customer, CustomerSegment, PriceType
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/customers")
ENTITY = "customer"


def _base(include_deleted: bool):
    stmt = select(Customer).order_by(Customer.name)
    if not include_deleted:
        stmt = stmt.where(Customer.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[CustomerRead])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("customer:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    segment: CustomerSegment | None = Query(default=None),
    price_type: PriceType | None = Query(default=None),
    manager_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    has_debt: bool | None = Query(
        default=None, description="True → current_debt > 0"
    ),
    over_limit: bool | None = Query(
        default=None,
        description="True → current_debt >= credit_limit (kredit limit>0)",
    ),
    include_deleted: bool = Query(default=False),
) -> Page[CustomerRead]:
    stmt = _base(include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Customer.name.ilike(like),
                Customer.inn.ilike(like),
                Customer.phone.ilike(like),
                Customer.email.ilike(like),
            )
        )
    if segment is not None:
        stmt = stmt.where(Customer.segment == segment)
    if price_type is not None:
        stmt = stmt.where(Customer.price_type == price_type)
    if manager_id is not None:
        stmt = stmt.where(Customer.manager_id == manager_id)
    if is_active is not None:
        stmt = stmt.where(Customer.is_active == is_active)
    if has_debt is True:
        stmt = stmt.where(Customer.current_debt > 0)
    elif has_debt is False:
        stmt = stmt.where(Customer.current_debt == 0)
    if over_limit is True:
        stmt = stmt.where(
            Customer.credit_limit > 0,
            Customer.current_debt >= Customer.credit_limit,
        )

    items, total, pages = await paginate(db, stmt, params)
    return Page[CustomerRead](
        items=[CustomerRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("customer:read")),
) -> CustomerRead:
    c = await db.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")
    return CustomerRead.model_validate(c)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:write")),
) -> CustomerRead:
    c = Customer(**body.model_dump())
    db.add(c)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "INN band") from e

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=c.id, changes=body.model_dump(), request=request,
    )
    await db.commit()
    await db.refresh(c)
    return CustomerRead.model_validate(c)


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:write")),
) -> CustomerRead:
    c = await db.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {
        "name", "legal_type", "inn", "phone", "email", "address",
        "segment", "price_type", "credit_limit", "manager_id", "notes", "is_active",
    }
    changes = diff_attrs(c, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(c, f, v)

    if changes:
        await log_activity(
            db, actor=actor, action=AuditAction.UPDATE,
            entity_type=ENTITY, entity_id=c.id, changes=changes, request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "INN band") from e
    await db.refresh(c)
    return CustomerRead.model_validate(c)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_customer(
    customer_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:delete")),
) -> None:
    c = await db.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")
    c.soft_delete()
    await log_activity(
        db, actor=actor, action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY, entity_id=c.id, request=request,
    )
    await db.commit()


@router.post("/{customer_id}/restore", response_model=CustomerRead)
async def restore_customer(
    customer_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:write")),
) -> CustomerRead:
    c = await db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")
    if c.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mijoz o'chirilmagan")
    c.restore()
    await log_activity(
        db, actor=actor, action=AuditAction.RESTORE,
        entity_type=ENTITY, entity_id=c.id, request=request,
    )
    await db.commit()
    await db.refresh(c)
    return CustomerRead.model_validate(c)
