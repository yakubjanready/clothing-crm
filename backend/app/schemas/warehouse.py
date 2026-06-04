from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.warehouse import WarehouseType


class WarehouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=32)
    type: WarehouseType = WarehouseType.MAIN
    address: str | None = Field(default=None, max_length=512)
    is_active: bool = True
    manager_id: uuid.UUID | None = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, min_length=1, max_length=32)
    type: WarehouseType | None = None
    address: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None
    manager_id: uuid.UUID | None = None


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    type: WarehouseType
    address: str | None = None
    is_active: bool
    manager_id: uuid.UUID | None = None
