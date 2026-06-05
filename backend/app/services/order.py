"""Order state machine va atomik tranzaksiyalar.

Funksiyalar `db.flush` qiladi, lekin commit chaqiruvchida (router) bajariladi.
Xato bo'lsa router rollback qiladi (HTTPException ko'tarib).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.order_return import Return, ReturnItem, ReturnStatus
from app.models.payment import Payment, PaymentMethod
from app.models.product_variant import ProductVariant
from app.services.customer import (
    CreditLimitExceededError,
    adjust_customer_debt,
    check_credit_limit,
)
from app.services.stock import (
    InsufficientStockError,
    InvalidMovementError,
    issue_stock,
    receive_stock,
    release_reservation,
    reserve_stock,
)

if TYPE_CHECKING:
    from app.models.user import User


# ---------- Xatolar ----------


class OrderError(Exception):
    """Order xizmatining bazaviy xatosi."""


class InvalidOrderTransitionError(OrderError):
    """Yaroqsiz status o'tishi (state machine)."""


class OrderValidationError(OrderError):
    """Yaroqsiz body — bo'sh order, noma'lum variant, ortiqcha to'lov va h.k."""


# ---------- State machine ----------

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


def assert_transition(current: OrderStatus, target: OrderStatus) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidOrderTransitionError(
            f"Order statusi {current} dan {target} ga o'tib bo'lmaydi. "
            f"Ruxsat etilgan: {sorted(s.value for s in allowed) or 'yoʼq'}"
        )


# ---------- Yordamchi ----------


def generate_order_number(prefix: str = "ORD") -> str:
    yyyymm = datetime.now(UTC).strftime("%Y%m")
    suffix = secrets.token_hex(3).upper()  # 6 hex
    return f"{prefix}-{yyyymm}-{suffix}"


async def _load_order(db: AsyncSession, order_id: uuid.UUID) -> Order | None:
    return (
        await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.deleted_at.is_(None))
            .options(selectinload(Order.items))
        )
    ).scalar_one_or_none()


async def _load_variants_map(
    db: AsyncSession, variant_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ProductVariant]:
    if not variant_ids:
        return {}
    rows = (
        (await db.execute(select(ProductVariant).where(ProductVariant.id.in_(variant_ids))))
        .scalars()
        .all()
    )
    return {v.id: v for v in rows}


def _recalculate_totals(order: Order) -> None:
    subtotal = sum((i.line_total for i in order.items), start=Decimal("0"))
    order.subtotal = subtotal
    order.total = max(Decimal("0"), subtotal - order.discount)


# ---------- Yaratish va tahrirlash ----------


async def build_draft_order(
    db: AsyncSession,
    *,
    customer_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    items_data: list[dict],
    discount: Decimal = Decimal("0"),
    notes: str | None = None,
    manager_id: uuid.UUID | None = None,
) -> Order:
    """DRAFT order yaratadi (commit chaqiruvchida)."""
    variant_ids = [i["variant_id"] for i in items_data]
    variants = await _load_variants_map(db, variant_ids)
    missing = [vid for vid in variant_ids if vid not in variants]
    if missing:
        raise OrderValidationError(f"variant_id topilmadi: {missing}")

    items_objs: list[OrderItem] = []
    for d in items_data:
        variant = variants[d["variant_id"]]
        unit_price = d.get("unit_price")
        if unit_price is None:
            unit_price = variant.wholesale_price
        qty = d["quantity"]
        line = (Decimal(qty) * Decimal(unit_price)).quantize(Decimal("0.01"))
        items_objs.append(
            OrderItem(
                variant_id=variant.id,
                quantity=qty,
                unit_price=Decimal(unit_price),
                line_total=line,
            )
        )

    order = Order(
        number=generate_order_number(),
        status=OrderStatus.DRAFT,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        manager_id=manager_id,
        notes=notes,
        discount=discount,
        items=items_objs,
    )
    _recalculate_totals(order)
    db.add(order)
    await db.flush()
    return order


async def replace_items(
    db: AsyncSession,
    *,
    order: Order,
    items_data: list[dict],
    discount: Decimal | None = None,
) -> Order:
    if order.status != OrderStatus.DRAFT:
        raise InvalidOrderTransitionError("Items faqat DRAFT statusda o'zgartiriladi")
    for it in list(order.items):
        await db.delete(it)
    order.items.clear()
    await db.flush()

    variants = await _load_variants_map(db, [i["variant_id"] for i in items_data])
    for d in items_data:
        variant = variants.get(d["variant_id"])
        if variant is None:
            raise OrderValidationError(f"variant_id topilmadi: {d['variant_id']}")
        unit_price = d.get("unit_price") or variant.wholesale_price
        qty = d["quantity"]
        line = (Decimal(qty) * Decimal(unit_price)).quantize(Decimal("0.01"))
        order.items.append(
            OrderItem(
                order_id=order.id,
                variant_id=variant.id,
                quantity=qty,
                unit_price=Decimal(unit_price),
                line_total=line,
            )
        )
    if discount is not None:
        order.discount = discount
    _recalculate_totals(order)
    await db.flush()
    return order


# ---------- State amallar ----------


async def confirm_order(db: AsyncSession, *, order: Order, actor: User | None) -> Order:
    """DRAFT → CONFIRMED. Kredit limit + qoldiqlarni reserve qiladi."""
    assert_transition(order.status, OrderStatus.CONFIRMED)
    if not order.items:
        raise OrderValidationError("Order bo'sh — kamida 1 item kerak")

    customer = await db.get(Customer, order.customer_id)
    if customer is None:
        raise OrderValidationError("Mijoz topilmadi")

    check_credit_limit(customer, order.total)

    for item in order.items:
        await reserve_stock(
            db,
            variant_id=item.variant_id,
            warehouse_id=order.warehouse_id,
            quantity=item.quantity,
            actor=actor,
            reason=f"order {order.number} confirm",
            reference_type="order",
            reference_id=order.id,
        )

    await adjust_customer_debt(db, customer=customer, delta=order.total, actor=actor)

    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = datetime.now(UTC)
    await db.flush()
    return order


async def pay_order(
    db: AsyncSession,
    *,
    order: Order,
    amount: Decimal,
    method: PaymentMethod,
    actor: User | None,
    notes: str | None = None,
) -> tuple[Order, Payment]:
    """CONFIRMED yoki SHIPPED → PAID (agar to'liq to'langan bo'lsa).
    Qisman to'lov ham qabul qilinadi.
    """
    if order.status not in {OrderStatus.CONFIRMED, OrderStatus.SHIPPED}:
        raise InvalidOrderTransitionError(
            f"Order {order.status} statusda — to'lov qabul qilinmaydi"
        )
    if amount <= 0:
        raise OrderValidationError("amount > 0 bo'lishi kerak")

    remaining = order.total - order.paid_amount
    if amount > remaining:
        raise OrderValidationError(f"To'lov qoldiqdan ortiq (qoldiq={remaining}, to'lov={amount})")

    customer = await db.get(Customer, order.customer_id)
    assert customer is not None  # FK ga ishongan holda
    await adjust_customer_debt(db, customer=customer, delta=-amount, actor=actor)

    payment = Payment(
        order_id=order.id,
        amount=amount,
        method=method,
        notes=notes,
        actor_id=actor.id if actor else None,
    )
    db.add(payment)

    order.paid_amount = order.paid_amount + amount
    if order.paid_amount >= order.total and order.status == OrderStatus.CONFIRMED:
        order.status = OrderStatus.PAID
        order.paid_at = datetime.now(UTC)
    elif order.paid_amount >= order.total and order.status == OrderStatus.SHIPPED:
        order.status = OrderStatus.COMPLETED

    await db.flush()
    return order, payment


async def ship_order(db: AsyncSession, *, order: Order, actor: User | None) -> Order:
    """CONFIRMED yoki PAID → SHIPPED (yoki COMPLETED agar paid).
    Reservni bo'shatadi va stockdan chiqaradi (OUT movement).
    """
    if order.status not in {OrderStatus.CONFIRMED, OrderStatus.PAID}:
        raise InvalidOrderTransitionError(f"Order {order.status} statusda — yuk berib bo'lmaydi")

    for item in order.items:
        await release_reservation(
            db,
            variant_id=item.variant_id,
            warehouse_id=order.warehouse_id,
            quantity=item.quantity,
            actor=actor,
            reason=f"order {order.number} ship",
            reference_type="order",
            reference_id=order.id,
        )
        await issue_stock(
            db,
            variant_id=item.variant_id,
            from_warehouse_id=order.warehouse_id,
            quantity=item.quantity,
            actor=actor,
            reason=f"order {order.number} ship",
            reference_type="order",
            reference_id=order.id,
        )

    order.shipped_at = datetime.now(UTC)
    if order.status == OrderStatus.PAID:
        order.status = OrderStatus.COMPLETED
    else:
        order.status = OrderStatus.SHIPPED
    await db.flush()
    return order


async def cancel_order(
    db: AsyncSession,
    *,
    order: Order,
    actor: User | None,
    reason: str | None = None,
) -> Order:
    """Cancel:
    - DRAFT: hech qanday ta'sir
    - CONFIRMED: reservni release, qarz orqaga (paid_amount mavjud bo'lsa,
      uni mijoz omonati sifatida saqlanadi — bu yerda refund tracker yo'q)
    - PAID: reserve release, qarz orqaga (paid_amount mijozning omonati)
    - SHIPPED: stockka qaytarish (receive), qarz orqaga
    """
    if order.status in {OrderStatus.COMPLETED, OrderStatus.CANCELLED}:
        raise InvalidOrderTransitionError(f"Order {order.status} — bekor qilib bo'lmaydi")

    customer = await db.get(Customer, order.customer_id)
    assert customer is not None  # FK ga ishongan holda

    if order.status == OrderStatus.CONFIRMED:
        for item in order.items:
            await release_reservation(
                db,
                variant_id=item.variant_id,
                warehouse_id=order.warehouse_id,
                quantity=item.quantity,
                actor=actor,
                reason=f"order {order.number} cancel",
                reference_type="order",
                reference_id=order.id,
            )
        remaining = order.total - order.paid_amount
        if remaining > 0:
            await adjust_customer_debt(db, customer=customer, delta=-remaining, actor=actor)

    elif order.status == OrderStatus.PAID:
        for item in order.items:
            await release_reservation(
                db,
                variant_id=item.variant_id,
                warehouse_id=order.warehouse_id,
                quantity=item.quantity,
                actor=actor,
                reason=f"order {order.number} cancel",
                reference_type="order",
                reference_id=order.id,
            )

    elif order.status == OrderStatus.SHIPPED:
        for item in order.items:
            await receive_stock(
                db,
                variant_id=item.variant_id,
                to_warehouse_id=order.warehouse_id,
                quantity=item.quantity,
                actor=actor,
                reason=f"order {order.number} cancel-after-ship",
                reference_type="order",
                reference_id=order.id,
            )
        remaining = order.total - order.paid_amount
        if remaining > 0:
            await adjust_customer_debt(db, customer=customer, delta=-remaining, actor=actor)

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.now(UTC)
    order.cancel_reason = reason
    await db.flush()
    return order


# ---------- Returns ----------


async def create_return(
    db: AsyncSession,
    *,
    order: Order,
    items_data: list[dict],
    actor: User | None,
    reason: str | None = None,
) -> Return:
    """Qaytarish so'rovi — REQUESTED holatda. Stock va balans `approve_return` da
    o'zgaradi."""
    if order.status not in {OrderStatus.SHIPPED, OrderStatus.COMPLETED}:
        raise InvalidOrderTransitionError(
            f"Order {order.status} — qaytarish faqat SHIPPED/COMPLETED uchun"
        )

    by_id = {i.id: i for i in order.items}
    ri_objs: list[ReturnItem] = []
    total_refund = Decimal("0")
    for d in items_data:
        oi = by_id.get(d["order_item_id"])
        if oi is None:
            raise OrderValidationError(f"order_item_id ushbu orderda yo'q: {d['order_item_id']}")
        qty = d["quantity"]
        if qty <= 0 or qty > oi.quantity:
            raise OrderValidationError(f"qty {qty} chegaradan tashqari (max {oi.quantity})")
        line = (Decimal(qty) * oi.unit_price).quantize(Decimal("0.01"))
        ri_objs.append(
            ReturnItem(
                order_item_id=oi.id,
                quantity=qty,
                unit_price=oi.unit_price,
                line_total=line,
            )
        )
        total_refund += line

    ret = Return(
        number=generate_order_number("RET"),
        order_id=order.id,
        status=ReturnStatus.REQUESTED,
        reason=reason,
        actor_id=actor.id if actor else None,
        total_refund=total_refund,
        items=ri_objs,
    )
    db.add(ret)
    await db.flush()
    return ret


async def approve_return(db: AsyncSession, *, ret: Return, actor: User | None) -> Return:
    """REQUESTED → APPROVED. Tovarni stockka qaytarish + mijoz qarzi/omonati."""
    if ret.status != ReturnStatus.REQUESTED:
        raise InvalidOrderTransitionError(f"Return {ret.status} — tasdiqlab bo'lmaydi")
    order = await db.get(Order, ret.order_id)
    assert order is not None  # FK ga ishongan holda
    customer = await db.get(Customer, order.customer_id)
    assert customer is not None

    # Stockka qaytarish
    for item in ret.items:
        oi = await db.get(OrderItem, item.order_item_id)
        assert oi is not None
        await receive_stock(
            db,
            variant_id=oi.variant_id,
            to_warehouse_id=order.warehouse_id,
            quantity=item.quantity,
            actor=actor,
            reason=f"return {ret.number}",
            reference_type="return",
            reference_id=ret.id,
        )

    # Balans:
    # Agar to'lanmagan qarz mavjud bo'lsa, refund_amount avval qarzdan ayriladi.
    # Qolgan qism mijozning omonati (bu yerda alohida track qilinmaydi —
    # adjust_customer_debt 0 ga to'xtaydi).
    if ret.total_refund > 0:
        await adjust_customer_debt(db, customer=customer, delta=-ret.total_refund, actor=actor)

    ret.status = ReturnStatus.APPROVED
    ret.processed_at = datetime.now(UTC)
    await db.flush()
    return ret


# ---------- Invoice ----------


async def create_invoice(db: AsyncSession, *, order: Order) -> Invoice:
    """Invoice yozuvi (PDF generatsiya keyin Celery'da)."""
    if order.status == OrderStatus.DRAFT:
        raise InvalidOrderTransitionError("DRAFT order uchun invoice yaratib bo'lmaydi")
    inv = Invoice(
        number=generate_order_number("INV"),
        order_id=order.id,
        status=InvoiceStatus.PENDING,
        total=order.total,
    )
    db.add(inv)
    await db.flush()
    return inv


# Re-export stock va customer xatolari (router'da bitta `except` ishlatish uchun)
__all__ = [
    "ALLOWED_TRANSITIONS",
    "CreditLimitExceededError",
    "InsufficientStockError",
    "InvalidMovementError",
    "InvalidOrderTransitionError",
    "OrderError",
    "OrderValidationError",
    "approve_return",
    "assert_transition",
    "build_draft_order",
    "cancel_order",
    "confirm_order",
    "create_invoice",
    "create_return",
    "generate_order_number",
    "pay_order",
    "replace_items",
    "ship_order",
]
