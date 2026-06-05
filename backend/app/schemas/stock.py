from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    warehouse_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    reserved: int
    min_quantity: int
    available: int  # property — quantity - reserved


class StockMinUpdate(BaseModel):
    min_quantity: int = Field(ge=0)


# --- Movement operatsiyalari ---


class _MovementBase(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=256)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: uuid.UUID | None = None


class MovementReceive(_MovementBase):
    to_warehouse_id: uuid.UUID


class MovementIssue(_MovementBase):
    from_warehouse_id: uuid.UUID


class MovementTransfer(_MovementBase):
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID


class MovementReserve(_MovementBase):
    warehouse_id: uuid.UUID


class MovementRelease(_MovementBase):
    warehouse_id: uuid.UUID


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    variant_id: uuid.UUID
    from_warehouse_id: uuid.UUID | None = None
    to_warehouse_id: uuid.UUID | None = None
    quantity: int
    reason: str | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
