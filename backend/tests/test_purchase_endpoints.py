"""Procurement moduli: /suppliers, /purchase-orders, /receive, /pay."""
from __future__ import annotations

import uuid as _uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_variant import ProductVariant
from app.models.purchase_order import PurchaseOrderStatus
from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.models.user import User
from app.services.purchase import (
    ALLOWED_TRANSITIONS,
    InvalidPurchaseTransitionError,
    assert_transition,
)


# ---- Fixtures ----

@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def sales_headers(client: AsyncClient, sales_user: User) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "SalesPass123!"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def catalog_setup(
    client: AsyncClient, admin_headers: dict[str, str]
) -> tuple[str, str]:
    cat = (await client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "Mayka"}
    )).json()
    prod = (await client.post(
        "/api/v1/products", headers=admin_headers,
        json={"name": "Klassik", "category_id": cat["id"]},
    )).json()
    var = (await client.post(
        f"/api/v1/products/{prod['id']}/variants", headers=admin_headers,
        json={"size": "M", "color": "Qora", "wholesale_price": "20000",
              "retail_price": "30000"},
    )).json()
    return prod["id"], var["id"]


@pytest.fixture
async def warehouse_id(
    client: AsyncClient, admin_headers: dict[str, str]
) -> str:
    w = (await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "Markaz", "code": "MAIN"},
    )).json()
    return w["id"]


@pytest.fixture
async def supplier_id(
    client: AsyncClient, admin_headers: dict[str, str]
) -> str:
    s = (await client.post(
        "/api/v1/suppliers", headers=admin_headers,
        json={"name": "Toshkent Tekstil LLC", "inn": "200123456", "rating": 4},
    )).json()
    return s["id"]


# ============ State machine pure ============

def test_state_machine_completeness() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(PurchaseOrderStatus)
    assert ALLOWED_TRANSITIONS[PurchaseOrderStatus.PAID] == set()
    assert ALLOWED_TRANSITIONS[PurchaseOrderStatus.CANCELLED] == set()


@pytest.mark.parametrize(
    "current,target,valid",
    [
        (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.RECEIVED, True),
        (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.CANCELLED, True),
        (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.PAID, True),
        (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PAID, False),
        (PurchaseOrderStatus.PAID, PurchaseOrderStatus.CANCELLED, False),
        (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED, False),
    ],
)
def test_transitions(
    current: PurchaseOrderStatus, target: PurchaseOrderStatus, valid: bool
) -> None:
    if valid:
        assert_transition(current, target)
    else:
        with pytest.raises(InvalidPurchaseTransitionError):
            assert_transition(current, target)


# ============ Suppliers CRUD ============

async def test_create_supplier_with_rating(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/suppliers", headers=admin_headers,
        json={"name": "Asia Textile", "rating": 5},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["rating"] == 5
    assert Decimal(body["current_debt"]) == Decimal("0")


async def test_supplier_name_unique_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/suppliers", headers=admin_headers, json={"name": "Dup"}
    )
    dup = await client.post(
        "/api/v1/suppliers", headers=admin_headers, json={"name": "Dup"}
    )
    assert dup.status_code == 409


async def test_supplier_filter_min_rating(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    for n, r in [("A", 1), ("B", 3), ("C", 5)]:
        await client.post(
            "/api/v1/suppliers", headers=admin_headers,
            json={"name": n, "rating": r},
        )
    r = await client.get(
        "/api/v1/suppliers", headers=admin_headers, params={"min_rating": 3}
    )
    assert r.json()["total"] == 2


async def test_sales_user_cannot_create_supplier(
    client: AsyncClient, sales_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/suppliers", headers=sales_headers, json={"name": "X"}
    )
    assert r.status_code == 403


# ============ PO create ============

async def test_create_po_draft_with_totals(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    r = await client.post(
        "/api/v1/purchase-orders", headers=admin_headers,
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_id,
            "items": [
                {"variant_id": variant_id, "quantity": 100, "unit_cost": "8000"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["number"].startswith("PO-")
    assert Decimal(body["total"]) == Decimal("800000")
    assert len(body["items"]) == 1


# ============ Receive flow ============

async def _create_po(client, headers, supplier_id, warehouse_id, variant_id, qty=10, cost="5000"):
    return (await client.post(
        "/api/v1/purchase-orders", headers=headers,
        json={
            "supplier_id": supplier_id, "warehouse_id": warehouse_id,
            "items": [{"variant_id": variant_id, "quantity": qty, "unit_cost": cost}],
        },
    )).json()


async def test_receive_creates_stock_and_updates_cost_and_debt(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(
        client, admin_headers, supplier_id, warehouse_id, variant_id, 50, "7500"
    )
    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "received"

    # Stock += 50 (yangi)
    stock = (await test_db.execute(
        select(Stock).where(Stock.variant_id == _uuid.UUID(variant_id))
    )).scalar_one()
    assert stock.quantity == 50

    # Variant cost_price = 7500 (latest)
    variant = await test_db.get(ProductVariant, _uuid.UUID(variant_id))
    await test_db.refresh(variant)
    assert variant.cost_price == Decimal("7500")

    # Supplier debt += 375000 (50 * 7500)
    supplier = await test_db.get(Supplier, _uuid.UUID(supplier_id))
    await test_db.refresh(supplier)
    assert supplier.current_debt == Decimal("375000")

    # StockMovement IN yozildi
    movs = (await test_db.execute(
        select(StockMovement).where(StockMovement.type == MovementType.IN)
    )).scalars().all()
    assert len(movs) == 1 and movs[0].quantity == 50


async def test_receive_updates_cost_to_latest_purchase(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    po1 = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 10, "5000")
    await client.post(f"/api/v1/purchase-orders/{po1['id']}/receive", headers=admin_headers)

    variant = await test_db.get(ProductVariant, _uuid.UUID(variant_id))
    await test_db.refresh(variant)
    assert variant.cost_price == Decimal("5000")

    # Ikkinchi PO yangi narx bilan
    po2 = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 5, "6500")
    await client.post(f"/api/v1/purchase-orders/{po2['id']}/receive", headers=admin_headers)

    await test_db.refresh(variant)
    assert variant.cost_price == Decimal("6500")  # latest


async def test_receive_draft_only(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id)
    await client.post(f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers)
    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers
    )
    assert r.status_code == 400


async def test_sales_user_cannot_receive(
    client: AsyncClient, admin_headers: dict[str, str], sales_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id)
    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive", headers=sales_headers
    )
    assert r.status_code == 403


# ============ Pay flow ============

async def test_pay_full_marks_paid_and_clears_debt(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 10, "5000")
    await client.post(f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers)

    # debt = 50000
    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/pay", headers=admin_headers,
        json={"amount": "50000", "method": "bank"},
    )
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["amount"]) == Decimal("50000")

    supplier = await test_db.get(Supplier, _uuid.UUID(supplier_id))
    await test_db.refresh(supplier)
    assert supplier.current_debt == Decimal("0")

    # PO status PAID
    list_resp = await client.get(
        f"/api/v1/purchase-orders/{po['id']}", headers=admin_headers
    )
    assert list_resp.json()["status"] == "paid"


async def test_pay_partial_keeps_received_status(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 10, "5000")
    await client.post(f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers)
    await client.post(
        f"/api/v1/purchase-orders/{po['id']}/pay", headers=admin_headers,
        json={"amount": "20000"},
    )
    detail = await client.get(
        f"/api/v1/purchase-orders/{po['id']}", headers=admin_headers
    )
    assert detail.json()["status"] == "received"
    assert Decimal(detail.json()["paid_amount"]) == Decimal("20000")

    supplier = await test_db.get(Supplier, _uuid.UUID(supplier_id))
    await test_db.refresh(supplier)
    assert supplier.current_debt == Decimal("30000")


async def test_pay_overpay_400(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 1, "100")
    await client.post(f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers)
    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/pay", headers=admin_headers,
        json={"amount": "999999"},
    )
    assert r.status_code == 400


async def test_pay_before_receive_400(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 1, "100")
    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/pay", headers=admin_headers,
        json={"amount": "50"},
    )
    assert r.status_code == 400


# ============ Cancel + balance ============

async def test_cancel_draft_only(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    po = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id)

    r = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/cancel", headers=admin_headers,
        json={"reason": "Yetkazib bermadi"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    # Endi cancel'dan keyin receive ishlamaydi
    r2 = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers
    )
    assert r2.status_code == 400


async def test_supplier_balance_aggregates(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str], warehouse_id: str, supplier_id: str,
) -> None:
    _, variant_id = catalog_setup
    # 2 ta PO: bittasi qabul qilingan + qisman to'lov, bittasi DRAFT
    p1 = await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 10, "1000")
    await client.post(f"/api/v1/purchase-orders/{p1['id']}/receive", headers=admin_headers)
    await client.post(
        f"/api/v1/purchase-orders/{p1['id']}/pay", headers=admin_headers,
        json={"amount": "3000"},
    )
    await _create_po(client, admin_headers, supplier_id, warehouse_id, variant_id, 2, "500")

    bal = (await client.get(
        f"/api/v1/suppliers/{supplier_id}/balance", headers=admin_headers
    )).json()
    assert bal["orders_total"] == 2
    assert bal["orders_received"] == 1
    assert bal["orders_paid"] == 0
    assert Decimal(bal["total_purchased"]) == Decimal("10000")
    assert Decimal(bal["total_paid"]) == Decimal("3000")
    assert Decimal(bal["current_debt"]) == Decimal("7000")
