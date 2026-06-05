"""Ombor operatsiyalarining atomik xizmati.

Funksiyalar commit qilmaydi — chaqiruvchi `await db.commit()` mas'uliyatini oladi.
Xato ko'tarilgan paytda chaqiruvchi `db.rollback()` qilishi kerak (FastAPI router
HTTPException ko'targanda yashiringan tarzda buni qiladi: dependency sessiyani yopadi
va atomik bo'lmagan o'zgarishlar transactiya bilan birga rollback bo'ladi).
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


class StockError(Exception):
    """Asosiy ombor xatolari."""


class InsufficientStockError(StockError):
    """Qoldiq yetarli emas."""


class InvalidMovementError(StockError):
    """Yaroqsiz operatsiya (manfiy/0 quantity, from==to va h.k.)."""


# ---------- Quyi qatlam ----------


async def _lock_stock(
    db: AsyncSession, warehouse_id: uuid.UUID, variant_id: uuid.UUID
) -> Stock | None:
    """SELECT ... FOR UPDATE — Postgres'da row-level lock; SQLite e'tiborsiz qoldiradi."""
    stmt = (
        select(Stock)
        .where(Stock.warehouse_id == warehouse_id, Stock.variant_id == variant_id)
        .with_for_update()
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _get_or_create_stock(
    db: AsyncSession, warehouse_id: uuid.UUID, variant_id: uuid.UUID
) -> Stock:
    stock = await _lock_stock(db, warehouse_id, variant_id)
    if stock is None:
        stock = Stock(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            quantity=0,
            reserved=0,
            min_quantity=0,
        )
        db.add(stock)
        await db.flush()
    return stock


def _build_movement(
    *,
    type_: MovementType,
    variant_id: uuid.UUID,
    quantity: int,
    actor: User | None,
    from_wh: uuid.UUID | None = None,
    to_wh: uuid.UUID | None = None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    return StockMovement(
        type=type_,
        variant_id=variant_id,
        from_warehouse_id=from_wh,
        to_warehouse_id=to_wh,
        quantity=quantity,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        actor_id=actor.id if actor else None,
    )


def _maybe_notify_low_stock(stock: Stock) -> None:
    """Stock o'zgarishidan keyin chaqiriladi. Available < min bo'lsa Celery task."""
    if stock.min_quantity <= 0:
        return
    available = stock.quantity - stock.reserved
    if available >= stock.min_quantity:
        return

    logger.warning(
        "low_stock stock_id=%s available=%s min=%s wh=%s variant=%s",
        stock.id,
        available,
        stock.min_quantity,
        stock.warehouse_id,
        stock.variant_id,
    )
    try:
        from app.tasks.celery_app import celery_app

        celery_app.send_task(
            "notify_low_stock",
            args=[
                str(stock.id),
                str(stock.warehouse_id),
                str(stock.variant_id),
                available,
                stock.min_quantity,
            ],
        )
    except Exception:
        logger.exception("low_stock celery dispatch failed")


# ---------- Yuqori qatlam operatsiyalari ----------


async def receive_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    quantity: int,
    actor: User | None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    """Kirim — to_warehouse'ga qo'shadi."""
    if quantity <= 0:
        raise InvalidMovementError("quantity > 0 bo'lishi kerak")

    stock = await _get_or_create_stock(db, to_warehouse_id, variant_id)
    stock.quantity += quantity

    mov = _build_movement(
        type_=MovementType.IN,
        variant_id=variant_id,
        quantity=quantity,
        actor=actor,
        to_wh=to_warehouse_id,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(mov)
    await db.flush()
    return mov


async def issue_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    from_warehouse_id: uuid.UUID,
    quantity: int,
    actor: User | None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    """Chiqim — from_warehouse'dan ayiradi. Yetmasa InsufficientStockError."""
    if quantity <= 0:
        raise InvalidMovementError("quantity > 0 bo'lishi kerak")

    stock = await _lock_stock(db, from_warehouse_id, variant_id)
    available = (stock.quantity - stock.reserved) if stock else 0
    if stock is None or available < quantity:
        raise InsufficientStockError(
            f"Yetarli qoldiq yo'q (available={available}, kerak={quantity})"
        )

    stock.quantity -= quantity
    mov = _build_movement(
        type_=MovementType.OUT,
        variant_id=variant_id,
        quantity=quantity,
        actor=actor,
        from_wh=from_warehouse_id,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(mov)
    await db.flush()
    _maybe_notify_low_stock(stock)
    return mov


async def transfer_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    quantity: int,
    actor: User | None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    """Atomik transfer: from -= quantity, to += quantity (bitta tranzaksiya)."""
    if quantity <= 0:
        raise InvalidMovementError("quantity > 0 bo'lishi kerak")
    if from_warehouse_id == to_warehouse_id:
        raise InvalidMovementError("from_warehouse_id == to_warehouse_id")

    from_stock = await _lock_stock(db, from_warehouse_id, variant_id)
    available = (from_stock.quantity - from_stock.reserved) if from_stock else 0
    if from_stock is None or available < quantity:
        raise InsufficientStockError(
            f"From-ombor qoldig'i yetmaydi (available={available}, kerak={quantity})"
        )

    to_stock = await _get_or_create_stock(db, to_warehouse_id, variant_id)

    from_stock.quantity -= quantity
    to_stock.quantity += quantity

    mov = _build_movement(
        type_=MovementType.TRANSFER,
        variant_id=variant_id,
        quantity=quantity,
        actor=actor,
        from_wh=from_warehouse_id,
        to_wh=to_warehouse_id,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(mov)
    await db.flush()
    _maybe_notify_low_stock(from_stock)
    return mov


async def reserve_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    actor: User | None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    """Rezerv — available'dan ayiradi (quantity o'zgarmaydi)."""
    if quantity <= 0:
        raise InvalidMovementError("quantity > 0 bo'lishi kerak")

    stock = await _lock_stock(db, warehouse_id, variant_id)
    available = (stock.quantity - stock.reserved) if stock else 0
    if stock is None or available < quantity:
        raise InsufficientStockError(
            f"Rezerv uchun yetarli available yo'q ({available} < {quantity})"
        )

    stock.reserved += quantity
    mov = _build_movement(
        type_=MovementType.RESERVE,
        variant_id=variant_id,
        quantity=quantity,
        actor=actor,
        from_wh=warehouse_id,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(mov)
    await db.flush()
    _maybe_notify_low_stock(stock)
    return mov


async def release_reservation(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int,
    actor: User | None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    """Rezervni bo'shatish — reserved -= quantity."""
    if quantity <= 0:
        raise InvalidMovementError("quantity > 0 bo'lishi kerak")

    stock = await _lock_stock(db, warehouse_id, variant_id)
    if stock is None or stock.reserved < quantity:
        raise InvalidMovementError(
            f"Bo'shatish uchun yetarli reserved yo'q "
            f"(reserved={stock.reserved if stock else 0}, kerak={quantity})"
        )

    stock.reserved -= quantity
    mov = _build_movement(
        type_=MovementType.RELEASE,
        variant_id=variant_id,
        quantity=quantity,
        actor=actor,
        from_wh=warehouse_id,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(mov)
    await db.flush()
    return mov


async def adjust_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    delta: int,
    actor: User | None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> StockMovement:
    """Inventarizatsiya farqi — delta musbat yoki manfiy bo'lishi mumkin."""
    if delta == 0:
        raise InvalidMovementError("delta != 0 bo'lishi kerak")
    stock = await _get_or_create_stock(db, warehouse_id, variant_id)
    new_qty = stock.quantity + delta
    if new_qty < stock.reserved:
        raise InsufficientStockError("Tuzatishdan keyin quantity < reserved bo'lib qoldi")
    stock.quantity = new_qty

    mov = _build_movement(
        type_=MovementType.ADJUST,
        variant_id=variant_id,
        quantity=abs(delta),
        actor=actor,
        from_wh=warehouse_id if delta < 0 else None,
        to_wh=warehouse_id if delta > 0 else None,
        reason=reason or "inventory adjustment",
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(mov)
    await db.flush()
    _maybe_notify_low_stock(stock)
    return mov
