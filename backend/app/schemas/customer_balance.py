from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CustomerBalanceResponse(BaseModel):
    customer_id: uuid.UUID
    name: str
    credit_limit: Decimal
    current_debt: Decimal
    available_credit: Decimal
    is_blocked: bool

    contacts_total: int
    primary_contact_name: str | None = None

    interactions_total: int
    last_interaction_at: datetime | None = None
    last_interaction_type: str | None = None
