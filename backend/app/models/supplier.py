from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.purchase_order import PurchaseOrder


class Supplier(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Yetkazib beruvchi. `current_debt` — biz unga qancha qarzdormiz."""

    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint("current_debt >= 0", name="ck_supplier_debt_nonneg"),
        CheckConstraint("rating >= 0 AND rating <= 5", name="ck_supplier_rating_0_5"),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    inn: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(128), nullable=True)

    rating: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    current_debt: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    purchase_orders: Mapped[list[PurchaseOrder]] = relationship(back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier {self.name} rating={self.rating} debt={self.current_debt}>"
