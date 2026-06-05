from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentMethod
from app.models.purchase_order import PurchaseOrderStatus

# ---- PurchaseItem ----


class PurchaseItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0, decimal_places=2)


class PurchaseItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    unit_cost: Decimal
    line_total: Decimal


# ---- PurchaseOrder ----


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    items: list[PurchaseItemCreate] = Field(min_length=1, max_length=200)
    notes: str | None = None
    manager_id: uuid.UUID | None = None


class PurchaseOrderUpdate(BaseModel):
    items: list[PurchaseItemCreate] | None = Field(default=None, min_length=1)
    notes: str | None = None
    manager_id: uuid.UUID | None = None


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    status: PurchaseOrderStatus
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    manager_id: uuid.UUID | None = None

    total: Decimal
    paid_amount: Decimal

    notes: str | None = None
    cancel_reason: str | None = None
    received_at: datetime | None = None
    paid_at: datetime | None = None
    cancelled_at: datetime | None = None

    items: list[PurchaseItemRead] = []


class SupplierPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: PaymentMethod = PaymentMethod.BANK
    notes: str | None = Field(default=None, max_length=256)


class SupplierPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    notes: str | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime


class POCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=512)
