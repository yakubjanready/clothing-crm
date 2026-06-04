from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Common declarative base. Biznes modellar ushbu sinfdan meros oladi."""


class UUIDPrimaryKeyMixin:
    """Birlamchi kalit — UUIDv4. Python tomonda generatsiya qilinadi (DB-portable)."""

    id: Mapped[_uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """TZ-aware created_at / updated_at. server_default = NOW() — DB tomondan to'ldiriladi."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """O'chirish o'rniga deleted_at ni belgilash. Repozitoriya darajasidagi filtr keyin qo'shiladi."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.deleted_at = None
