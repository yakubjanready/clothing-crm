from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    inn: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=512)
    contact_person: str | None = Field(default=None, max_length=128)
    rating: int = Field(default=0, ge=0, le=5)
    notes: str | None = None
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    inn: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=512)
    contact_person: str | None = Field(default=None, max_length=128)
    rating: int | None = Field(default=None, ge=0, le=5)
    notes: str | None = None
    is_active: bool | None = None


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    inn: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    contact_person: str | None = None
    rating: int
    current_debt: Decimal
    notes: str | None = None
    is_active: bool


class SupplierBalance(BaseModel):
    supplier_id: uuid.UUID
    name: str
    current_debt: Decimal
    rating: int
    orders_total: int
    orders_received: int
    orders_paid: int
    total_purchased: Decimal
    total_paid: Decimal
