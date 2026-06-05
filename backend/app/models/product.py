from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attribute_value import AttributeValue
    from app.models.brand import Brand
    from app.models.category import Category
    from app.models.product_variant import ProductVariant


class Gender(StrEnum):
    MEN = "men"
    WOMEN = "women"
    UNISEX = "unisex"
    KIDS = "kids"
    BOYS = "boys"
    GIRLS = "girls"


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    sku_prefix: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gender: Mapped[Gender] = mapped_column(
        String(16), nullable=False, default=Gender.UNISEX, index=True
    )
    images: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: Mapped[Category] = relationship(back_populates="products")
    brand: Mapped[Brand | None] = relationship(back_populates="products")
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    attribute_values: Mapped[list[AttributeValue]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Product {self.sku_prefix} {self.name}>"
