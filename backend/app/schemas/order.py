from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus

# ---- OrderItem ----


class OrderItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="None bo'lsa variant.wholesale_price snapshot olinadi",
    )


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal


# ---- Order ----


class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    warehouse_id: uuid.UUID
    items: list[OrderItemCreate] = Field(min_length=1, max_length=200)
    discount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    notes: str | None = None
    manager_id: uuid.UUID | None = None


class OrderUpdate(BaseModel):
    """Faqat DRAFT statusda — items o'rnini bosadi."""

    items: list[OrderItemCreate] | None = Field(default=None, min_length=1, max_length=200)
    discount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    notes: str | None = None
    manager_id: uuid.UUID | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    status: OrderStatus
    customer_id: uuid.UUID
    warehouse_id: uuid.UUID
    manager_id: uuid.UUID | None = None

    subtotal: Decimal
    discount: Decimal
    total: Decimal
    paid_amount: Decimal

    notes: str | None = None
    cancel_reason: str | None = None
    confirmed_at: datetime | None = None
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    cancelled_at: datetime | None = None

    items: list[OrderItemRead] = []


class CancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=512)
