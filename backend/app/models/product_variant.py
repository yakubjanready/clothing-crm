from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Mahsulot varianti — o'lcham + rang kombinatsiyasi. SKU global unique va avto."""

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size", "color", name="uq_variant_size_color"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    size: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    color_hex: Mapped[str | None] = mapped_column(String(9), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    wholesale_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    retail_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    product: Mapped["Product"] = relationship(back_populates="variants")

    def __repr__(self) -> str:
        return f"<Variant {self.sku} {self.size}/{self.color}>"
