from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationSeverity, NotificationType


class NotificationCreate(BaseModel):
    """Admin tomonidan qo'lda yaratish (testlar/eslatma uchun)."""

    type: NotificationType = NotificationType.INFO
    severity: NotificationSeverity = NotificationSeverity.INFO
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=1024)
    user_id: uuid.UUID | None = Field(default=None, description="None bo'lsa — broadcast")
    data: dict[str, Any] | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    data: dict[str, Any] | None = None
    read_at: datetime | None = None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int
