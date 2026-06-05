from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AccountType(StrEnum):
    CASH = "cash"  # naqd kassa
    BANK = "bank"  # bank hisobi
    CARD = "card"  # plastik karta
    OTHER = "other"


class Account(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Moliyaviy hisob — kassa/bank/karta. Balans real vaqtda yangilanadi."""

    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_account_balance_nonneg"),)

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    type: Mapped[AccountType] = mapped_column(
        String(16), nullable=False, default=AccountType.CASH, index=True
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="UZS", server_default=text("'UZS'")
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    def __repr__(self) -> str:
        return f"<Account {self.name} {self.type} balance={self.balance}>"
