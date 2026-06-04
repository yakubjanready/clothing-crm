from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerContactBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    position: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=512)


class CustomerContactCreate(CustomerContactBase):
    pass


class CustomerContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    full_name: str
    position: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    is_primary: bool
    notes: str | None = None
