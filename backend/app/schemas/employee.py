from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.employee import EmployeeStatus


class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    photo_url: str | None = Field(default=None, max_length=512)
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    hire_date: date | None = None
    termination_date: date | None = None
    department_id: uuid.UUID
    position_id: uuid.UUID
    user_id: uuid.UUID | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    photo_url: str | None = Field(default=None, max_length=512)
    status: EmployeeStatus | None = None
    hire_date: date | None = None
    termination_date: date | None = None
    department_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    photo_url: str | None = None
    status: EmployeeStatus
    hire_date: date | None = None
    termination_date: date | None = None
    department_id: uuid.UUID
    position_id: uuid.UUID
    user_id: uuid.UUID | None = None


class EmployeeFilter(BaseModel):
    search: str | None = None  # first_name/last_name/email
    department_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    status: EmployeeStatus | None = None
    include_deleted: bool = False
