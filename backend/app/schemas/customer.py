from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.customer import CustomerSegment, PriceType


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_type: str | None = Field(default=None, max_length=32)
    inn: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=512)
    segment: CustomerSegment = CustomerSegment.NEW
    price_type: PriceType = PriceType.WHOLESALE
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    manager_id: uuid.UUID | None = None
    notes: str | None = None
    is_active: bool = True


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_type: str | None = Field(default=None, max_length=32)
    inn: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=512)
    segment: CustomerSegment | None = None
    price_type: PriceType | None = None
    credit_limit: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    manager_id: uuid.UUID | None = None
    notes: str | None = None
    is_active: bool | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    legal_type: str | None = None
    inn: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    segment: CustomerSegment
    price_type: PriceType
    credit_limit: Decimal
    current_debt: Decimal
    manager_id: uuid.UUID | None = None
    notes: str | None = None
    is_active: bool
