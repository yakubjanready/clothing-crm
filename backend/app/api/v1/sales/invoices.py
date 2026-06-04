from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.schemas.invoice import InvoiceRead
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/invoices")


@router.get("", response_model=Page[InvoiceRead])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("order:read")),
    params: PageParams = Depends(page_params),
    order_id: uuid.UUID | None = Query(default=None),
    status_: InvoiceStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=64),
) -> Page[InvoiceRead]:
    stmt = select(Invoice).order_by(Invoice.issued_at.desc())
    if order_id is not None:
        stmt = stmt.where(Invoice.order_id == order_id)
    if status_ is not None:
        stmt = stmt.where(Invoice.status == status_)
    if search:
        stmt = stmt.where(Invoice.number.ilike(f"%{search}%"))

    items, total, pages = await paginate(db, stmt, params)
    return Page[InvoiceRead](
        items=[InvoiceRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("order:read")),
) -> InvoiceRead:
    inv = await db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice topilmadi")
    return InvoiceRead.model_validate(inv)
