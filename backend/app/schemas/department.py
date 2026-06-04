from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=512)
    parent_id: uuid.UUID | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=512)
    parent_id: uuid.UUID | None = None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None = None
    description: str | None = None
    parent_id: uuid.UUID | None = None


class DepartmentFilter(BaseModel):
    search: str | None = None
    parent_id: uuid.UUID | None = None
    include_deleted: bool = False
