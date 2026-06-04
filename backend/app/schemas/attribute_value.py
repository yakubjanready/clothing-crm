from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class AttributeValueBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=512)


class AttributeValueCreate(AttributeValueBase):
    pass


class AttributeValueUpdate(BaseModel):
    value: str | None = Field(default=None, min_length=1, max_length=512)


class AttributeValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    name: str
    value: str
