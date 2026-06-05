from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee import Employee


class Position(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Lavozim — asosiy maosh va (ixtiyoriy) bo'limga bog'liqlik."""

    __tablename__ = "positions"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    department: Mapped[Department | None] = relationship(back_populates="positions")
    employees: Mapped[list[Employee]] = relationship(back_populates="position")

    def __repr__(self) -> str:
        return f"<Position {self.name}>"
