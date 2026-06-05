from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import AccountType


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    type: AccountType = AccountType.CASH
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=512)
    bank_name: str | None = Field(default=None, max_length=128)
    account_number: str | None = Field(default=None, max_length=64)
    is_active: bool = True


class AccountCreate(AccountBase):
    initial_balance: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    type: AccountType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=512)
    bank_name: str | None = Field(default=None, max_length=128)
    account_number: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None = None
    type: AccountType
    currency: str
    balance: Decimal
    description: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    is_active: bool
