from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product_variant import ProductVariant
    from app.models.user import User
    from app.models.warehouse import Warehouse


class InventoryStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Inventory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Inventarizatsiya sessiyasi — ombor bo'yicha qoldiqlarni faktik sanab chiqish."""

    __tablename__ = "inventories"

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[InventoryStatus] = mapped_column(
        String(16),
        nullable=False,
        default=InventoryStatus.IN_PROGRESS,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    warehouse: Mapped[Warehouse] = relationship()
    actor: Mapped[User | None] = relationship()
    items: Mapped[list[InventoryItem]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InventoryItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("inventory_id", "variant_id", name="uq_inventory_item"),)

    inventory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counted_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    inventory: Mapped[Inventory] = relationship(back_populates="items")
    variant: Mapped[ProductVariant] = relationship()

    @property
    def difference(self) -> int:
        return self.counted_quantity - self.expected_quantity
