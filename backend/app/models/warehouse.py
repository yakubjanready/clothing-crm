from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock
    from app.models.user import User


class WarehouseType(StrEnum):
    MAIN = "main"  # asosiy ombor
    BRANCH = "branch"  # filial
    OUTLET = "outlet"  # do'kon
    TRANSIT = "transit"  # tranzit (yo'ldagi)
    DEFECTIVE = "defective"  # nuqsonli mahsulotlar


class Warehouse(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    type: Mapped[WarehouseType] = mapped_column(
        String(16), nullable=False, default=WarehouseType.MAIN, index=True
    )
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    manager: Mapped[User | None] = relationship()
    stocks: Mapped[list[Stock]] = relationship(back_populates="warehouse")

    def __repr__(self) -> str:
        return f"<Warehouse {self.code} {self.type}>"
