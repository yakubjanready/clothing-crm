from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associations import role_permissions, user_roles

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User


class RoleName(StrEnum):
    ADMIN = "admin"
    DIRECTOR = "director"
    MANAGER = "manager"
    SALES = "sales"
    WAREHOUSE = "warehouse"
    ACCOUNTANT = "accountant"
    COURIER = "courier"


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
