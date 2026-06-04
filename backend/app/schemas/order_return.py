from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order_return import ReturnStatus


class ReturnItemCreate(BaseModel):
    order_item_id: uuid.UUID
    quantity: int = Field(gt=0)


class ReturnItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    return_id: uuid.UUID
    order_item_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class ReturnCreate(BaseModel):
    order_id: uuid.UUID
    items: list[ReturnItemCreate] = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=512)


class ReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    order_id: uuid.UUID
    status: ReturnStatus
    reason: str | None = None
    total_refund: Decimal
    actor_id: uuid.UUID | None = None
    processed_at: datetime | None = None
    items: list[ReturnItemRead] = []
