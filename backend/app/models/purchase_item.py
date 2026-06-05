from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product_variant import ProductVariant
    from app.models.purchase_order import PurchaseOrder


class PurchaseItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pi_qty_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_pi_cost_nonneg"),
    )

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    variant: Mapped[ProductVariant] = relationship()

    def __repr__(self) -> str:
        return f"<PurchaseItem variant={self.variant_id} qty={self.quantity}>"
