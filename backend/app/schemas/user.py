"""Foydalanuvchilarni boshqarish (admin) uchun schema'lar."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth import RoleRead, UserRead


class UserListItem(UserRead):
    """Ro'yxat elementi — UserRead bilan bir xil, lekin alohida turi modellashtirish uchun."""


class UserUpdate(BaseModel):
    """Admin tomonidan foydalanuvchini yangilash. Barcha maydonlar ixtiyoriy."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    role_ids: list[uuid.UUID] | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class RoleListRead(BaseModel):
    """Rol ro'yxatda chiqarish — permission code'lari bilan."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    permission_codes: list[str] = Field(default_factory=list)


__all__ = [
    "UserRead",
    "UserListItem",
    "UserUpdate",
    "PasswordReset",
    "RoleRead",
    "RoleListRead",
    "EmailStr",
]
