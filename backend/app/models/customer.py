from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    from app.models.customer_contact import CustomerContact
    from app.models.customer_interaction import CustomerInteraction
    from app.models.user import User


class CustomerSegment(StrEnum):
    VIP = "vip"
    REGULAR = "regular"
    NEW = "new"
    INACTIVE = "inactive"


class PriceType(StrEnum):
    WHOLESALE = "wholesale"  # ulgurji
    RETAIL = "retail"        # chakana
    SPECIAL = "special"      # individual shartnoma


class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("credit_limit >= 0", name="ck_customer_credit_limit_nonneg"),
        CheckConstraint("current_debt >= 0", name="ck_customer_debt_nonneg"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    inn: Mapped[str | None] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)

    segment: Mapped[CustomerSegment] = mapped_column(
        String(16), nullable=False, default=CustomerSegment.NEW, index=True
    )
    price_type: Mapped[PriceType] = mapped_column(
        String(16), nullable=False, default=PriceType.WHOLESALE, index=True
    )

    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default=text("0"),
    )
    current_debt: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default=text("0"),
    )

    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    manager: Mapped["User | None"] = relationship()
    contacts: Mapped[list["CustomerContact"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    interactions: Mapped[list["CustomerInteraction"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    # ---- Hisoblanadigan ----
    @property
    def available_credit(self) -> Decimal:
        return self.credit_limit - self.current_debt

    @property
    def is_blocked(self) -> bool:
        """Kredit limit oshib ketgan yoki to'liq band."""
        return self.current_debt >= self.credit_limit and self.credit_limit > 0

    def __repr__(self) -> str:
        return f"<Customer {self.name} segment={self.segment} debt={self.current_debt}>"
