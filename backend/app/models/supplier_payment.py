from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.payment import PaymentMethod

if TYPE_CHECKING:
    from app.models.purchase_order import PurchaseOrder
    from app.models.user import User


class SupplierPayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Supplier'ga qilingan to'lov yozuvi."""

    __tablename__ = "supplier_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_supplier_payment_amount_positive"),)

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        String(16), nullable=False, default=PaymentMethod.BANK, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="payments")
    actor: Mapped[User | None] = relationship()

    def __repr__(self) -> str:
        return f"<SupplierPayment {self.method} amount={self.amount}>"
