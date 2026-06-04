from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.customer_interaction import InteractionType


class CustomerInteractionCreate(BaseModel):
    type: InteractionType
    subject: str = Field(min_length=1, max_length=255)
    notes: str | None = None
    occurred_at: datetime | None = None  # None bo'lsa server now()
    follow_up_at: datetime | None = None


class CustomerInteractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    type: InteractionType
    subject: str
    notes: str | None = None
    occurred_at: datetime
    follow_up_at: datetime | None = None
    created_at: datetime
