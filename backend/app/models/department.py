from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.position import Position


class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Tashkilot bo'limi — daraxt strukturasi (self-FK parent_id)."""

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
    )
    children: Mapped[list[Department]] = relationship(
        "Department",
        back_populates="parent",
    )
    positions: Mapped[list[Position]] = relationship(
        back_populates="department",
    )
    employees: Mapped[list[Employee]] = relationship(
        back_populates="department",
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"
