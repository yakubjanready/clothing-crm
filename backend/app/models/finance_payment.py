from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class PaymentDirection(StrEnum):
    INCOME = "income"     # kirim (account.balance +=)
    EXPENSE = "expense"   # chiqim (account.balance -=)


class FinanceCategory(StrEnum):
    CUSTOMER_PAYMENT = "customer_payment"   # mijoz to'lovi (income)
    SUPPLIER_PAYMENT = "supplier_payment"   # supplier'ga (expense)
    EXPENSE = "expense"                      # umumiy xarajat (ish haqi/ijara/...)
    TRANSFER = "transfer"                    # kassalararo o'tkazma
    OTHER = "other"


class FinancePayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Moliyaviy to'lov yozuvi — o'zgarmas. Har bir Account o'zgarishi shu yerda."""

    __tablename__ = "finance_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_fp_amount_positive"),
    )

    number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    direction: Mapped[PaymentDirection] = mapped_column(
        String(16), nullable=False, index=True
    )
    category: Mapped[FinanceCategory] = mapped_column(
        String(32), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    related_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    reference_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    related_account: Mapped["Account | None"] = relationship(
        foreign_keys=[related_account_id]
    )
    actor: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<FinancePayment {self.number} {self.direction} amount={self.amount}>"
