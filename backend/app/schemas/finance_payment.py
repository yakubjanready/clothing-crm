from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance_payment import FinanceCategory, PaymentDirection


class FinancePaymentCreate(BaseModel):
    direction: PaymentDirection
    category: FinanceCategory = FinanceCategory.OTHER
    account_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    description: str | None = Field(default=None, max_length=512)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: uuid.UUID | None = None


class TransferRequest(BaseModel):
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    description: str | None = Field(default=None, max_length=512)


class FinancePaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    direction: PaymentDirection
    category: FinanceCategory
    account_id: uuid.UUID
    related_account_id: uuid.UUID | None = None
    amount: Decimal
    description: str | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime


class TransferResponse(BaseModel):
    out_payment: FinancePaymentRead
    in_payment: FinancePaymentRead
