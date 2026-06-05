from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User


class InteractionType(StrEnum):
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"
    SMS = "sms"
    VISIT = "visit"
    OTHER = "other"


class CustomerInteraction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mijoz bilan o'zaro aloqa yozuvi — o'zgarmas tarix (soft-delete yo'q)."""

    __tablename__ = "customer_interactions"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[InteractionType] = mapped_column(String(16), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="interactions")
    actor: Mapped[User | None] = relationship()

    def __repr__(self) -> str:
        return f"<Interaction {self.type} {self.subject!r}>"
