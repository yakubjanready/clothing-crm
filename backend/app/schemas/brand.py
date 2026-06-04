from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=512)
    country: str | None = Field(default=None, max_length=64)
    logo_url: str | None = Field(default=None, max_length=512)


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    slug: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=512)
    country: str | None = Field(default=None, max_length=64)
    logo_url: str | None = Field(default=None, max_length=512)


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    country: str | None = None
    logo_url: str | None = None
