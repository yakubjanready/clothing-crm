from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VariantColorSpec(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    hex: str | None = Field(default=None, max_length=9)


class VariantBase(BaseModel):
    size: str = Field(min_length=1, max_length=16)
    color: str = Field(min_length=1, max_length=64)
    color_hex: str | None = Field(default=None, max_length=9)
    wholesale_price: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    retail_price: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    barcode: str | None = Field(default=None, max_length=64)
    image_url: str | None = Field(default=None, max_length=512)
    is_active: bool = True


class VariantCreate(VariantBase):
    pass


class VariantUpdate(BaseModel):
    size: str | None = Field(default=None, min_length=1, max_length=16)
    color: str | None = Field(default=None, min_length=1, max_length=64)
    color_hex: str | None = Field(default=None, max_length=9)
    wholesale_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    retail_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    barcode: str | None = Field(default=None, max_length=64)
    image_url: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    size: str
    color: str
    color_hex: str | None = None
    wholesale_price: Decimal
    retail_price: Decimal
    barcode: str | None = None
    image_url: str | None = None
    is_active: bool


class VariantMatrixRequest(BaseModel):
    """size × color kombinatsiyalarini bir martada yaratish."""
    sizes: list[str] = Field(min_length=1, max_length=20)
    colors: list[VariantColorSpec] = Field(min_length=1, max_length=20)
    wholesale_price: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    retail_price: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    is_active: bool = True

    @field_validator("sizes")
    @classmethod
    def sizes_unique_nonempty(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("sizes takrorlanmasligi kerak")
        return cleaned

    @field_validator("colors")
    @classmethod
    def colors_unique_nonempty(cls, v: list[VariantColorSpec]) -> list[VariantColorSpec]:
        names = [c.name.strip() for c in v]
        if len(names) != len(set(names)):
            raise ValueError("colors.name takrorlanmasligi kerak")
        return v


class VariantMatrixResponse(BaseModel):
    created: list[VariantRead]
    skipped_existing: list[dict[str, str]]  # [{size, color}]
