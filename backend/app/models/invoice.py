from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order


class InvoiceStatus(StrEnum):
    PENDING = "pending"  # PDF generatsiya kutilmoqda (Celery'da)
    READY = "ready"  # PDF tayyor
    FAILED = "failed"  # generatsiya xatoligi


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoices"

    number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        String(16), nullable=False, default=InvoiceStatus.PENDING, index=True
    )
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice {self.number} {self.status}>"
