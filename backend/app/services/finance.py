"""Moliyaviy tranzaksiyalar — Account balansi, FinancePayment, DebtRecord.
Funksiyalar `db.flush` qiladi; commit chaqiruvchida (router).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.debt_record import DebtDirection, DebtPartyType, DebtRecord
from app.models.finance_payment import (
    FinanceCategory,
    FinancePayment,
    PaymentDirection,
)
from app.services.order import generate_order_number

if TYPE_CHECKING:
    from app.models.user import User


class FinanceError(Exception):
    """Asosiy moliya xatosi."""


class InsufficientFundsError(FinanceError):
    """Account'da yetarli mablag' yo'q."""


class InvalidTransferError(FinanceError):
    """Yaroqsiz transfer (from==to, account topilmadi va h.k.)."""


async def _load_active_account(db: AsyncSession, account_id: uuid.UUID) -> Account:
    acc = await db.get(Account, account_id)
    if acc is None or acc.deleted_at is not None:
        raise FinanceError(f"Account topilmadi: {account_id}")
    if not acc.is_active:
        raise FinanceError(f"Account faol emas: {acc.name}")
    return acc


# ---------- Income / Expense ----------


async def record_income(
    db: AsyncSession,
    *,
    account_id: uuid.UUID,
    amount: Decimal,
    category: FinanceCategory = FinanceCategory.OTHER,
    description: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    actor: User | None = None,
) -> FinancePayment:
    if amount <= 0:
        raise FinanceError("amount > 0 bo'lishi kerak")
    acc = await _load_active_account(db, account_id)

    payment = FinancePayment(
        number=generate_order_number("FP"),
        direction=PaymentDirection.INCOME,
        category=category,
        account_id=account_id,
        amount=amount,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        actor_id=actor.id if actor else None,
    )
    db.add(payment)
    acc.balance = acc.balance + amount
    await db.flush()
    return payment


async def record_expense(
    db: AsyncSession,
    *,
    account_id: uuid.UUID,
    amount: Decimal,
    category: FinanceCategory = FinanceCategory.EXPENSE,
    description: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    actor: User | None = None,
) -> FinancePayment:
    if amount <= 0:
        raise FinanceError("amount > 0 bo'lishi kerak")
    acc = await _load_active_account(db, account_id)
    if acc.balance < amount:
        raise InsufficientFundsError(
            f"'{acc.name}' hisobida yetarli mablag' yo'q (balance={acc.balance}, kerak={amount})"
        )

    payment = FinancePayment(
        number=generate_order_number("FP"),
        direction=PaymentDirection.EXPENSE,
        category=category,
        account_id=account_id,
        amount=amount,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        actor_id=actor.id if actor else None,
    )
    db.add(payment)
    acc.balance = acc.balance - amount
    await db.flush()
    return payment


# ---------- Transfer ----------


async def transfer_funds(
    db: AsyncSession,
    *,
    from_account_id: uuid.UUID,
    to_account_id: uuid.UUID,
    amount: Decimal,
    actor: User | None,
    description: str | None = None,
) -> tuple[FinancePayment, FinancePayment]:
    """Kassalararo o'tkazma — atomik. Ikkala account ham yangilanadi va
    bir-biriga `related_account_id` orqali bog'langan ikki yozuv yaratiladi."""
    if amount <= 0:
        raise FinanceError("amount > 0 bo'lishi kerak")
    if from_account_id == to_account_id:
        raise InvalidTransferError("from_account_id == to_account_id")

    from_acc = await _load_active_account(db, from_account_id)
    to_acc = await _load_active_account(db, to_account_id)

    if from_acc.balance < amount:
        raise InsufficientFundsError(
            f"'{from_acc.name}' hisobida yetarli mablag' yo'q "
            f"(balance={from_acc.balance}, kerak={amount})"
        )

    from_acc.balance = from_acc.balance - amount
    to_acc.balance = to_acc.balance + amount

    desc = description or f"Transfer: {from_acc.name} -> {to_acc.name}"
    actor_id = actor.id if actor else None

    out_payment = FinancePayment(
        number=generate_order_number("FP"),
        direction=PaymentDirection.EXPENSE,
        category=FinanceCategory.TRANSFER,
        account_id=from_account_id,
        related_account_id=to_account_id,
        amount=amount,
        description=desc,
        actor_id=actor_id,
    )
    in_payment = FinancePayment(
        number=generate_order_number("FP"),
        direction=PaymentDirection.INCOME,
        category=FinanceCategory.TRANSFER,
        account_id=to_account_id,
        related_account_id=from_account_id,
        amount=amount,
        description=desc,
        actor_id=actor_id,
    )
    db.add(out_payment)
    db.add(in_payment)
    await db.flush()
    return out_payment, in_payment


# ---------- Debt ledger ----------


async def record_debt_change(
    db: AsyncSession,
    *,
    party_type: DebtPartyType,
    party_id: uuid.UUID,
    delta: Decimal,
    balance_after: Decimal,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    actor: User | None = None,
) -> DebtRecord | None:
    """delta != 0 bo'lsa DebtRecord yozadi. delta musbat=qarz oshdi,
    manfiy=qarz kamaydi."""
    if delta == 0:
        return None
    direction = DebtDirection.INCREASE if delta > 0 else DebtDirection.DECREASE
    record = DebtRecord(
        party_type=party_type,
        party_id=party_id,
        direction=direction,
        amount=abs(delta),
        balance_after=balance_after,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        actor_id=actor.id if actor else None,
    )
    db.add(record)
    await db.flush()
    return record


__all__ = [
    "FinanceError",
    "InsufficientFundsError",
    "InvalidTransferError",
    "record_debt_change",
    "record_expense",
    "record_income",
    "transfer_funds",
]
