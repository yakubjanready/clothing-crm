from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product import Product


class AttributeValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mahsulotning qo'shimcha xususiyatlari (material, fit, season, ...).
    Bir mahsulot uchun (name) noyob: bir mahsulotda bitta 'material' bo'lsin.
    """

    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("product_id", "name", name="uq_attribute_product_name"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(512), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="attribute_values")

    def __repr__(self) -> str:
        return f"<Attr {self.name}={self.value!r}>"
