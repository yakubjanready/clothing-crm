from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.debt_record import DebtDirection, DebtPartyType


class DebtRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    party_type: DebtPartyType
    party_id: uuid.UUID
    direction: DebtDirection
    amount: Decimal
    balance_after: Decimal
    reason: str | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime
