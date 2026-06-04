from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.invoice import InvoiceStatus


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    order_id: uuid.UUID
    status: InvoiceStatus
    total: Decimal
    pdf_url: str | None = None
    issued_at: datetime
