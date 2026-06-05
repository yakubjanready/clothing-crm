from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.finance_payment import (
    FinanceCategory,
    FinancePayment,
    PaymentDirection,
)
from app.models.user import User
from app.schemas.finance_payment import (
    FinancePaymentCreate,
    FinancePaymentRead,
    TransferRequest,
    TransferResponse,
)
from app.services.audit import log_activity
from app.services.finance import (
    FinanceError,
    InsufficientFundsError,
    InvalidTransferError,
    record_expense,
    record_income,
    transfer_funds,
)
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/payments")


def _raise(e: Exception) -> None:
    if isinstance(e, InsufficientFundsError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    if isinstance(e, (InvalidTransferError, FinanceError)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    raise e


@router.get("", response_model=Page[FinancePaymentRead])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("accounting:read")),
    params: PageParams = Depends(page_params),
    direction: PaymentDirection | None = Query(default=None),
    category: FinanceCategory | None = Query(default=None),
    account_id: uuid.UUID | None = Query(default=None),
    reference_type: str | None = Query(default=None, max_length=64),
) -> Page[FinancePaymentRead]:
    stmt = select(FinancePayment).order_by(FinancePayment.created_at.desc())
    if direction is not None:
        stmt = stmt.where(FinancePayment.direction == direction)
    if category is not None:
        stmt = stmt.where(FinancePayment.category == category)
    if account_id is not None:
        stmt = stmt.where(FinancePayment.account_id == account_id)
    if reference_type is not None:
        stmt = stmt.where(FinancePayment.reference_type == reference_type)

    items, total, pages = await paginate(db, stmt, params)
    return Page[FinancePaymentRead](
        items=[FinancePaymentRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.post("", response_model=FinancePaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: FinancePaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("accounting:write")),
) -> FinancePaymentRead:
    """Oddiy income yoki expense. Transfer alohida /transfer endpoint orqali."""
    if body.category == FinanceCategory.TRANSFER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Transfer uchun /payments/transfer endpoint'idan foydalaning",
        )
    try:
        fn = record_income if body.direction == PaymentDirection.INCOME else record_expense
        payment = await fn(
            db,
            account_id=body.account_id,
            amount=body.amount,
            category=body.category,
            description=body.description,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
            actor=actor,
        )
    except Exception as e:
        await db.rollback()
        _raise(e)

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="finance_payment",
        entity_id=payment.id,
        changes={
            "direction": body.direction,
            "category": body.category,
            "account_id": str(body.account_id),
            "amount": str(body.amount),
        },
        request=request,
    )
    await db.commit()
    await db.refresh(payment)
    return FinancePaymentRead.model_validate(payment)


@router.post("/transfer", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def transfer(
    body: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("accounting:write")),
) -> TransferResponse:
    try:
        out_p, in_p = await transfer_funds(
            db,
            from_account_id=body.from_account_id,
            to_account_id=body.to_account_id,
            amount=body.amount,
            actor=actor,
            description=body.description,
        )
    except Exception as e:
        await db.rollback()
        _raise(e)

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="finance_payment",
        entity_id=out_p.id,
        changes={
            "transfer_from": str(body.from_account_id),
            "transfer_to": str(body.to_account_id),
            "amount": str(body.amount),
        },
        request=request,
    )
    await db.commit()
    await db.refresh(out_p)
    await db.refresh(in_p)
    return TransferResponse(
        out_payment=FinancePaymentRead.model_validate(out_p),
        in_payment=FinancePaymentRead.model_validate(in_p),
    )
