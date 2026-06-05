"""Purchase order state machine va atomik tranzaksiyalar.

Funksiyalar `db.flush` qiladi, commit chaqiruvchida (router).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payment import PaymentMethod
from app.models.product_variant import ProductVariant
from app.models.purchase_item import PurchaseItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.services.order import generate_order_number
from app.services.stock import receive_stock

if TYPE_CHECKING:
    from app.models.user import User


# ---------- Xatolar ----------

class PurchaseError(Exception):
    pass


class InvalidPurchaseTransitionError(PurchaseError):
    pass


class PurchaseValidationError(PurchaseError):
    pass


# ---------- State machine ----------

ALLOWED_TRANSITIONS: dict[PurchaseOrderStatus, set[PurchaseOrderStatus]] = {
    PurchaseOrderStatus.DRAFT:     {PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.RECEIVED:  {PurchaseOrderStatus.PAID},
    PurchaseOrderStatus.PAID:      set(),
    PurchaseOrderStatus.CANCELLED: set(),
}


def assert_transition(
    current: PurchaseOrderStatus, target: PurchaseOrderStatus
) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidPurchaseTransitionError(
            f"PO statusi {current} dan {target} ga o'tib bo'lmaydi. "
            f"Ruxsat etilgan: {sorted(s.value for s in allowed) or 'yo`q'}"
        )


# ---------- Yaratish ----------

async def _load_variants_map(
    db: AsyncSession, variant_ids: list[uuid.UUID]
) -> dict[uuid.UUID, ProductVariant]:
    if not variant_ids:
        return {}
    rows = (
        await db.execute(
            select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
        )
    ).scalars().all()
    return {v.id: v for v in rows}


def _calc_total(items: list[PurchaseItem]) -> Decimal:
    return sum((i.line_total for i in items), start=Decimal("0"))


async def build_draft_purchase(
    db: AsyncSession,
    *,
    supplier_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    items_data: list[dict],
    notes: str | None = None,
    manager_id: uuid.UUID | None = None,
) -> PurchaseOrder:
    variant_ids = [i["variant_id"] for i in items_data]
    variants = await _load_variants_map(db, variant_ids)
    missing = [vid for vid in variant_ids if vid not in variants]
    if missing:
        raise PurchaseValidationError(f"variant_id topilmadi: {missing}")

    items_objs: list[PurchaseItem] = []
    for d in items_data:
        qty = d["quantity"]
        unit_cost = Decimal(d["unit_cost"])
        line = (Decimal(qty) * unit_cost).quantize(Decimal("0.01"))
        items_objs.append(
            PurchaseItem(
                variant_id=d["variant_id"],
                quantity=qty,
                unit_cost=unit_cost,
                line_total=line,
            )
        )

    po = PurchaseOrder(
        number=generate_order_number("PO"),
        status=PurchaseOrderStatus.DRAFT,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        manager_id=manager_id,
        notes=notes,
        total=_calc_total(items_objs),
        items=items_objs,
    )
    db.add(po)
    await db.flush()
    return po


async def replace_items(
    db: AsyncSession, *, po: PurchaseOrder, items_data: list[dict]
) -> PurchaseOrder:
    if po.status != PurchaseOrderStatus.DRAFT:
        raise InvalidPurchaseTransitionError("Items faqat DRAFT statusda o'zgartiriladi")
    for it in list(po.items):
        await db.delete(it)
    po.items.clear()
    await db.flush()

    variants = await _load_variants_map(db, [i["variant_id"] for i in items_data])
    new_items: list[PurchaseItem] = []
    for d in items_data:
        if d["variant_id"] not in variants:
            raise PurchaseValidationError(f"variant_id topilmadi: {d['variant_id']}")
        qty = d["quantity"]
        unit_cost = Decimal(d["unit_cost"])
        line = (Decimal(qty) * unit_cost).quantize(Decimal("0.01"))
        new_items.append(
            PurchaseItem(
                purchase_order_id=po.id,
                variant_id=d["variant_id"],
                quantity=qty,
                unit_cost=unit_cost,
                line_total=line,
            )
        )
    po.items.extend(new_items)
    po.total = _calc_total(new_items)
    await db.flush()
    return po


# ---------- State amallar ----------

async def receive_purchase(
    db: AsyncSession, *, po: PurchaseOrder, actor: "User | None"
) -> PurchaseOrder:
    """DRAFT → RECEIVED. Har item uchun:
    - stock += quantity (IN movement)
    - ProductVariant.cost_price = unit_cost (latest cost strategiyasi)
    - supplier.current_debt += po.total
    """
    assert_transition(po.status, PurchaseOrderStatus.RECEIVED)
    if not po.items:
        raise PurchaseValidationError("PO bo'sh — kamida 1 item kerak")

    for item in po.items:
        await receive_stock(
            db,
            variant_id=item.variant_id,
            to_warehouse_id=po.warehouse_id,
            quantity=item.quantity,
            actor=actor,
            reason=f"PO {po.number} receive",
            reference_type="purchase_order",
            reference_id=po.id,
        )
        # Tannarx yangilash — latest cost
        variant = await db.get(ProductVariant, item.variant_id)
        if variant is not None:
            variant.cost_price = item.unit_cost

    supplier = await db.get(Supplier, po.supplier_id)
    supplier.current_debt = supplier.current_debt + po.total

    po.status = PurchaseOrderStatus.RECEIVED
    po.received_at = datetime.now(timezone.utc)
    await db.flush()
    return po


async def pay_supplier(
    db: AsyncSession,
    *,
    po: PurchaseOrder,
    amount: Decimal,
    method: PaymentMethod,
    actor: "User | None",
    notes: str | None = None,
) -> tuple[PurchaseOrder, SupplierPayment]:
    """RECEIVED → (qisman to'lov: RECEIVED qoladi; to'liq: PAID).
    Supplier.current_debt -= amount.
    """
    if po.status != PurchaseOrderStatus.RECEIVED:
        raise InvalidPurchaseTransitionError(
            f"PO {po.status} statusda — to'lov qabul qilinmaydi"
        )
    if amount <= 0:
        raise PurchaseValidationError("amount > 0 bo'lishi kerak")
    remaining = po.total - po.paid_amount
    if amount > remaining:
        raise PurchaseValidationError(
            f"To'lov qoldiqdan ortiq (qoldiq={remaining}, to'lov={amount})"
        )

    supplier = await db.get(Supplier, po.supplier_id)
    new_debt = supplier.current_debt - amount
    supplier.current_debt = max(Decimal("0"), new_debt)

    payment = SupplierPayment(
        purchase_order_id=po.id,
        amount=amount,
        method=method,
        notes=notes,
        actor_id=actor.id if actor else None,
    )
    db.add(payment)

    po.paid_amount = po.paid_amount + amount
    if po.paid_amount >= po.total:
        po.status = PurchaseOrderStatus.PAID
        po.paid_at = datetime.now(timezone.utc)

    await db.flush()
    return po, payment


async def cancel_purchase(
    db: AsyncSession,
    *,
    po: PurchaseOrder,
    actor: "User | None",
    reason: str | None = None,
) -> PurchaseOrder:
    """Bekor qilish. DRAFT'dan tashqari holatda ruxsat etilmaydi
    (RECEIVED'dan qaytarish alohida workflow talab qiladi)."""
    if po.status != PurchaseOrderStatus.DRAFT:
        raise InvalidPurchaseTransitionError(
            f"PO {po.status} — faqat DRAFT bekor qilinadi"
        )
    po.status = PurchaseOrderStatus.CANCELLED
    po.cancelled_at = datetime.now(timezone.utc)
    po.cancel_reason = reason
    await db.flush()
    return po


# ---------- Reload helper (router uchun) ----------

async def reload_with_items(db: AsyncSession, po_id: uuid.UUID) -> PurchaseOrder:
    return (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.items))
        )
    ).scalar_one()


__all__ = [
    "PurchaseError", "InvalidPurchaseTransitionError", "PurchaseValidationError",
    "ALLOWED_TRANSITIONS", "assert_transition",
    "build_draft_purchase", "replace_items",
    "receive_purchase", "pay_supplier", "cancel_purchase",
    "reload_with_items",
]
