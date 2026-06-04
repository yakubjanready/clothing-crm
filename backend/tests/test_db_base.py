"""db/base.py mixinlari uchun testlar. Biznes modeli yo'q — test uchun
alohida `TestBase.metadata` ichida `Sample` modelini quramiz, shunda Base.metadata
ifloslanmaydi va alembic autogenerate'ga bog'liqlik tushmaydi.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase

from app.db.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class _TestBase(DeclarativeBase):
    """Alohida metadata — ishlab chiqarish Base.metadata'siga aralashmaydi."""


class Sample(_TestBase, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sample"


# ---- Schema (column metadata) testlari ----

def test_id_column_is_uuid_primary_key() -> None:
    col = Sample.__table__.c.id
    assert col.primary_key is True
    assert isinstance(col.type, Uuid)
    assert col.nullable is False
    generated = col.default.arg(None)
    assert isinstance(generated, _uuid.UUID)


def test_timestamp_columns_present_with_tz_and_server_default() -> None:
    for name in ("created_at", "updated_at"):
        col = Sample.__table__.c[name]
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None


def test_updated_at_has_onupdate() -> None:
    assert Sample.__table__.c.updated_at.onupdate is not None


def test_deleted_at_is_nullable_tz_aware_timestamp() -> None:
    col = Sample.__table__.c.deleted_at
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True
    assert col.nullable is True


# ---- SoftDeleteMixin xulq-atvori testlari ----

@pytest.fixture
def sample() -> Sample:
    s = Sample()
    s.id = _uuid.uuid4()
    return s


def test_soft_delete_sets_tz_aware_utc(sample: Sample) -> None:
    assert sample.is_deleted is False
    assert sample.deleted_at is None

    sample.soft_delete()

    assert sample.is_deleted is True
    assert isinstance(sample.deleted_at, datetime)
    assert sample.deleted_at.tzinfo is not None
    assert sample.deleted_at.utcoffset() == timezone.utc.utcoffset(sample.deleted_at)


def test_restore_clears_deleted_at(sample: Sample) -> None:
    sample.soft_delete()
    assert sample.is_deleted is True
    sample.restore()
    assert sample.is_deleted is False
    assert sample.deleted_at is None


# ---- db modulining eksporti testlari ----

def test_db_module_reexports() -> None:
    from app import db

    assert db.Base is not None
    assert db.UUIDPrimaryKeyMixin is UUIDPrimaryKeyMixin
    assert db.TimestampMixin is TimestampMixin
    assert db.SoftDeleteMixin is SoftDeleteMixin
    assert callable(db.get_db)
    assert callable(db.dispose_engine)
