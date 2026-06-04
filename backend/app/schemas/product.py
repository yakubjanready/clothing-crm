from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import Gender


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    material: str | None = Field(default=None, max_length=128)
    gender: Gender = Gender.UNISEX
    images: list[str] = Field(default_factory=list)
    is_active: bool = True
    category_id: uuid.UUID
    brand_id: uuid.UUID | None = None


class ProductCreate(ProductBase):
    slug: str | None = Field(default=None, max_length=320)
    sku_prefix: str | None = Field(default=None, max_length=32)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=320)
    description: str | None = None
    material: str | None = Field(default=None, max_length=128)
    gender: Gender | None = None
    images: list[str] | None = None
    is_active: bool | None = None
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    sku_prefix: str
    description: str | None = None
    material: str | None = None
    gender: Gender
    images: list[str] = []
    is_active: bool
    category_id: uuid.UUID
    brand_id: uuid.UUID | None = None
