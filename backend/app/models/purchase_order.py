from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.purchase_item import PurchaseItem
    from app.models.supplier import Supplier
    from app.models.supplier_payment import SupplierPayment
    from app.models.user import User
    from app.models.warehouse import Warehouse


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    RECEIVED = "received"
    PAID = "paid"
    CANCELLED = "cancelled"


class PurchaseOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_po_total_nonneg"),
        CheckConstraint("paid_amount >= 0", name="ck_po_paid_nonneg"),
    )

    number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        String(16), nullable=False, default=PurchaseOrderStatus.DRAFT, index=True
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    supplier: Mapped[Supplier] = relationship(back_populates="purchase_orders")
    warehouse: Mapped[Warehouse] = relationship()
    manager: Mapped[User | None] = relationship()
    items: Mapped[list[PurchaseItem]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list[SupplierPayment]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.total - self.paid_amount

    def __repr__(self) -> str:
        return f"<PO {self.number} {self.status} total={self.total}>"
