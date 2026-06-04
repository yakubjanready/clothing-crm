from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MovementType(StrEnum):
    IN = "in"               # kirim (to_warehouse)
    OUT = "out"             # chiqim (from_warehouse)
    TRANSFER = "transfer"   # bir ombordan boshqasiga
    RESERVE = "reserve"     # rezerv qilish
    RELEASE = "release"     # rezervni bo'shatish
    ADJUST = "adjust"       # inventarizatsiya farqi


class StockMovement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """O'zgarmas yozuv — har bir stock o'zgarishi shu jadvalga tushadi."""

    __tablename__ = "stock_movements"

    type: Mapped[MovementType] = mapped_column(
        String(16), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    to_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Movement {self.type} variant={self.variant_id} qty={self.quantity}>"
