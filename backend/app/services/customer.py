"""Mijoz xizmatlari — kredit limit tekshiruvi va qarz tuzatishi."""
from __future__ import annotations

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
) -> "Customer":
    """Mijoz qarzini delta ga o'zgartiradi.

    - delta > 0 — qarz oshadi (kredit beriladi) — limit tekshiriladi
    - delta < 0 — qarz kamayadi (to'lov keladi) — tekshiruv shart emas, lekin
      qarz manfiy bo'lib qolmasligi uchun cheklanadi (overpay → 0 ga to'xtatiladi).
    Caller commit qilishi shart.
    """
    if delta > 0:
        check_credit_limit(customer, delta)
        customer.current_debt = customer.current_debt + delta
    else:
        new_debt = customer.current_debt + delta
        customer.current_debt = max(Decimal("0"), new_debt)
    await db.flush()
    return customer
