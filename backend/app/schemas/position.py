from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PositionBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=512)
    base_salary: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    department_id: uuid.UUID | None = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=512)
    base_salary: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    department_id: uuid.UUID | None = None


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None = None
    description: str | None = None
    base_salary: Decimal
    department_id: uuid.UUID | None = None


class PositionFilter(BaseModel):
    search: str | None = None
    department_id: uuid.UUID | None = None
    include_deleted: bool = False
