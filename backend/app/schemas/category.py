from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=512)
    image_url: str | None = Field(default=None, max_length=512)
    parent_id: uuid.UUID | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    slug: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=512)
    image_url: str | None = Field(default=None, max_length=512)
    parent_id: uuid.UUID | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    parent_id: uuid.UUID | None = None
