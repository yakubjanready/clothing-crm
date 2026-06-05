from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Brand(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    products: Mapped[list[Product]] = relationship(back_populates="brand")

    def __repr__(self) -> str:
        return f"<Brand {self.name}>"
