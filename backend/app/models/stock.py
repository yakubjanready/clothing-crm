from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product_variant import ProductVariant
    from app.models.warehouse import Warehouse


class Stock(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Variant + ombor uchun bitta yozuv. quantity = jami fizik qoldiq;
    reserved = rezerv qilingan; available = quantity - reserved.
    """

    __tablename__ = "stocks"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "variant_id", name="uq_stock_wh_variant"),
        CheckConstraint("quantity >= 0", name="ck_stock_qty_nonneg"),
        CheckConstraint("reserved >= 0", name="ck_stock_reserved_nonneg"),
        CheckConstraint("reserved <= quantity", name="ck_stock_reserved_lte_qty"),
        CheckConstraint("min_quantity >= 0", name="ck_stock_min_nonneg"),
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reserved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    min_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    warehouse: Mapped[Warehouse] = relationship(back_populates="stocks")
    variant: Mapped[ProductVariant] = relationship()

    @property
    def available(self) -> int:
        return self.quantity - self.reserved

    def __repr__(self) -> str:
        return (
            f"<Stock wh={self.warehouse_id} variant={self.variant_id} "
            f"qty={self.quantity} reserved={self.reserved}>"
        )
