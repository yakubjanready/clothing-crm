from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class DebtPartyType(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class DebtDirection(StrEnum):
    INCREASE = "increase"  # qarz oshdi
    DECREASE = "decrease"  # qarz kamaydi


class DebtRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Qarz ledger yozuvi — o'zgarmas. Customer/Supplier qarzining har o'zgarishida
    yoziladi (yangi balans, harakat sababi va manbasi bilan).
    """

    __tablename__ = "debt_records"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_debt_amount_positive"),
    )

    party_type: Mapped[DebtPartyType] = mapped_column(
        String(16), nullable=False, index=True
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    direction: Mapped[DebtDirection] = mapped_column(
        String(16), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    actor: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<DebtRecord {self.party_type} {self.party_id} "
            f"{self.direction} {self.amount} → {self.balance_after}>"
        )
