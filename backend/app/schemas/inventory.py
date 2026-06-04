from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory import InventoryStatus


class InventoryCreate(BaseModel):
    warehouse_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=512)


class InventoryItemCount(BaseModel):
    variant_id: uuid.UUID
    counted_quantity: int = Field(ge=0)


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_id: uuid.UUID
    variant_id: uuid.UUID
    expected_quantity: int
    counted_quantity: int
    difference: int


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    warehouse_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    status: InventoryStatus
    notes: str | None = None
    finished_at: datetime | None = None
    items: list[InventoryItemRead] = []


class InventoryFinalizeResponse(BaseModel):
    inventory_id: uuid.UUID
    adjustments: int  # nechta variant tuzatildi
    status: InventoryStatus
