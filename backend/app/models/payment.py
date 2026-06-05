from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class PaymentMethod(StrEnum):
    CASH = "cash"
    BANK = "bank"
    TERMINAL = "terminal"
    OTHER = "other"


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_amount_positive"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        String(16), nullable=False, default=PaymentMethod.CASH, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    order: Mapped[Order] = relationship(back_populates="payments")
    actor: Mapped[User | None] = relationship()

    def __repr__(self) -> str:
        return f"<Payment {self.method} amount={self.amount}>"
