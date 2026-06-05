from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(StrEnum):
    LOW_STOCK = "low_stock"
    NEW_ORDER = "new_order"
    ORDER_CONFIRMED = "order_confirmed"
    PAYMENT_RECEIVED = "payment_received"
    DEBT_INCREASED = "debt_increased"
    PURCHASE_RECEIVED = "purchase_received"
    INFO = "info"


class NotificationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """In-app notifikatsiya. user_id NULL bo'lsa — barchaga (broadcast)."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[NotificationSeverity] = mapped_column(
        String(16), nullable=False, default=NotificationSeverity.INFO, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    sent_via_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    sent_via_telegram: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    user: Mapped[User | None] = relationship()

    @property
    def is_broadcast(self) -> bool:
        return self.user_id is None

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def __repr__(self) -> str:
        return f"<Notification {self.type} {self.severity} {self.title!r}>"
