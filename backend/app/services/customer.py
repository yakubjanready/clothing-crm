"""Mijoz xizmatlari — kredit limit tekshiruvi va qarz tuzatishi."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User


class CustomerError(Exception):
    """Mijoz xizmatining bazaviy xatosi."""


class CreditLimitExceededError(CustomerError):
    """Kredit limit oshib ketishi taklif qilinmoqda."""


def check_credit_limit(customer: "Customer", additional_debt: Decimal) -> None:
    """Yangi qarzni qo'shgandan keyin limit oshmasligini tekshiradi.

    - Agar `additional_debt <= 0` → tekshiruv talab etilmaydi (qarz oshmaydi).
    - Agar `customer.credit_limit == 0` → kredit umuman ruxsat etilmagan
      (har qanday musbat additional_debt xato beradi).
    - Agar `current_debt + additional_debt > credit_limit` → xato.
    """
    if additional_debt <= 0:
        return

    new_debt = customer.current_debt + additional_debt
    if customer.credit_limit <= 0:
        raise CreditLimitExceededError(
            f"Mijoz kreditga ruxsat etilmagan (credit_limit=0), so'ralgan={additional_debt}"
        )
    if new_debt > customer.credit_limit:
        over = new_debt - customer.credit_limit
        raise CreditLimitExceededError(
            f"Kredit limit oshib ketadi: yangi qarz={new_debt}, "
            f"limit={customer.credit_limit}, oshib ketgan summa={over}"
        )


async def adjust_customer_debt(
    db: AsyncSession,
    *,
    customer: "Customer",
    delta: Decimal,
    actor: "User | None" = None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> "Customer":
    """Mijoz qarzini delta ga o'zgartiradi va DebtRecord yozadi.

    - delta > 0 — qarz oshadi (kredit) — limit tekshiriladi
    - delta < 0 — qarz kamayadi (to'lov); overpay → 0 ga to'xtatiladi
    Caller commit qilishi shart.
    """
    from app.models.debt_record import DebtPartyType
    from app.services.finance import record_debt_change

    old_debt = customer.current_debt
    if delta > 0:
        check_credit_limit(customer, delta)
        customer.current_debt = customer.current_debt + delta
    else:
        new_debt = customer.current_debt + delta
        customer.current_debt = max(Decimal("0"), new_debt)
    actual_delta = customer.current_debt - old_debt
    await db.flush()

    if actual_delta != 0:
        await record_debt_change(
            db,
            party_type=DebtPartyType.CUSTOMER,
            party_id=customer.id,
            delta=actual_delta,
            balance_after=customer.current_debt,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            actor=actor,
        )
    return customer


async def adjust_supplier_debt(
    db: AsyncSession,
    *,
    supplier,
    delta: Decimal,
    actor: "User | None" = None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
):
    """Supplier qarzini delta ga o'zgartiradi va DebtRecord yozadi.

    - delta > 0 — biz qarzga oldik (supplier'ga qarzdormiz)
    - delta < 0 — to'lov qildik
    Overpay → 0 ga to'xtatiladi.
    """
    from app.models.debt_record import DebtPartyType
    from app.services.finance import record_debt_change

    old_debt = supplier.current_debt
    new_debt = supplier.current_debt + delta
    supplier.current_debt = max(Decimal("0"), new_debt)
    actual_delta = supplier.current_debt - old_debt
    await db.flush()

    if actual_delta != 0:
        await record_debt_change(
            db,
            party_type=DebtPartyType.SUPPLIER,
            party_id=supplier.id,
            delta=actual_delta,
            balance_after=supplier.current_debt,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            actor=actor,
        )
    return supplier
