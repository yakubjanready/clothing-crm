"""/orders, /invoices, /returns endpointlari uchun integratsion testlar."""

from __future__ import annotations

import uuid as _uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.stock import Stock
from app.models.user import User

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
async def catalog_setup(client: AsyncClient, admin_headers: dict[str, str]) -> tuple[str, str]:
    """1 ta kategoriya + 1 mahsulot + 1 variant (narx 10000)."""
    cat = (
        await client.post("/api/v1/categories", headers=admin_headers, json={"name": "Mayka"})
    ).json()
    prod = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={"name": "Klassik", "category_id": cat["id"]},
        )
    ).json()
    var = (
        await client.post(
            f"/api/v1/products/{prod['id']}/variants",
            headers=admin_headers,
            json={
                "size": "M",
                "color": "Qora",
                "wholesale_price": "10000",
                "retail_price": "15000",
            },
        )
    ).json()
    return prod["id"], var["id"]


@pytest.fixture
async def warehouse_id(client: AsyncClient, admin_headers: dict[str, str]) -> str:
    w = (
        await client.post(
            "/api/v1/warehouses",
            headers=admin_headers,
            json={"name": "Markaz", "code": "MAIN"},
        )
    ).json()
    return w["id"]


@pytest.fixture
async def customer_id(client: AsyncClient, admin_headers: dict[str, str]) -> str:
    c = (
        await client.post(
            "/api/v1/customers",
            headers=admin_headers,
            json={"name": "Mijoz", "credit_limit": "1000000"},
        )
    ).json()
    return c["id"]


async def _stock_qty(test_db: AsyncSession, variant_id: str) -> int:
    s = (
        await test_db.execute(select(Stock).where(Stock.variant_id == _uuid.UUID(variant_id)))
    ).scalar_one_or_none()
    return s.quantity if s else 0


async def _stock(test_db: AsyncSession, variant_id: str) -> Stock | None:
    return (
        await test_db.execute(select(Stock).where(Stock.variant_id == _uuid.UUID(variant_id)))
    ).scalar_one_or_none()


# ============ Create draft ============


async def test_create_draft_order_with_auto_number_and_totals(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    r = await client.post(
        "/api/v1/orders",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_id,
            "items": [{"variant_id": variant_id, "quantity": 5}],
            "discount": "1000",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["number"].startswith("ORD-")
    assert Decimal(body["subtotal"]) == Decimal("50000")  # 5*10000
    assert Decimal(body["total"]) == Decimal("49000")  # -1000 discount
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


async def test_create_order_validates_variant_existence(
    client: AsyncClient,
    admin_headers: dict[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    r = await client.post(
        "/api/v1/orders",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_id,
            "items": [{"variant_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}],
        },
    )
    assert r.status_code == 400


# ============ Confirm flow ============


async def _create_order(client, headers, customer_id, warehouse_id, variant_id, qty=5):
    return (
        await client.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "customer_id": customer_id,
                "warehouse_id": warehouse_id,
                "items": [{"variant_id": variant_id, "quantity": qty}],
            },
        )
    ).json()


async def _stock_in(client, headers, variant_id, warehouse_id, qty):
    return await client.post(
        "/api/v1/stock/movements/receive",
        headers=headers,
        json={"variant_id": variant_id, "to_warehouse_id": warehouse_id, "quantity": qty},
    )


async def test_confirm_reserves_stock_and_increases_debt(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)

    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    r = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "confirmed"

    s = await _stock(test_db, variant_id)
    assert s.quantity == 10 and s.reserved == 5 and s.available == 5

    cust = await test_db.get(Customer, _uuid.UUID(customer_id))
    await test_db.refresh(cust)
    assert cust.current_debt == Decimal("50000")


async def test_confirm_insufficient_stock_409(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 2)  # yetmaydi

    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    r = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    assert r.status_code == 409
    # Stockda hech narsa rezerv qilinmaganini tasdiqlash
    s = await _stock(test_db, variant_id)
    assert s.reserved == 0


async def test_confirm_blocked_by_credit_limit(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)

    # Limiti past mijoz
    poor = (
        await client.post(
            "/api/v1/customers",
            headers=admin_headers,
            json={"name": "Past limit", "credit_limit": "10000"},
        )
    ).json()
    order = await _create_order(client, admin_headers, poor["id"], warehouse_id, variant_id, 5)
    r = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    assert r.status_code == 409
    assert "limit" in r.json()["detail"].lower()
    # Stock o'zgarmasligi
    s = await _stock(test_db, variant_id)
    assert s.reserved == 0


async def test_sales_user_cannot_confirm_403(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sales_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, sales_headers, customer_id, warehouse_id, variant_id, 2)
    r = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=sales_headers)
    assert r.status_code == 403


# ============ Pay flow ============


async def test_pay_full_marks_paid_and_reduces_debt(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)

    r = await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_headers,
        json={"amount": "50000", "method": "cash"},
    )
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["amount"]) == Decimal("50000")

    o = await test_db.get(Order, _uuid.UUID(order["id"]))
    await test_db.refresh(o)
    assert o.status == OrderStatus.PAID
    assert o.paid_amount == Decimal("50000")

    cust = await test_db.get(Customer, _uuid.UUID(customer_id))
    await test_db.refresh(cust)
    assert cust.current_debt == Decimal("0")


async def test_pay_partial_keeps_confirmed_status(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_headers,
        json={"amount": "20000"},
    )
    o = await test_db.get(Order, _uuid.UUID(order["id"]))
    await test_db.refresh(o)
    assert o.status == OrderStatus.CONFIRMED
    assert o.paid_amount == Decimal("20000")


async def test_pay_overpay_400(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    r = await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_headers,
        json={"amount": "999999"},
    )
    assert r.status_code == 400


# ============ Ship flow ============


async def test_ship_decrements_stock_and_releases_reservation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 4)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_headers,
        json={"amount": "40000"},
    )

    r = await client.post(f"/api/v1/orders/{order['id']}/ship", headers=admin_headers)
    assert r.status_code == 200, r.text
    # PAID + ship → COMPLETED
    assert r.json()["status"] == "completed"

    s = await _stock(test_db, variant_id)
    assert s.quantity == 6 and s.reserved == 0


# ============ Cancel flow ============


async def test_cancel_confirmed_releases_reserve_and_debt(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)

    r = await client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Mijoz fikrini o'zgartirdi"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    s = await _stock(test_db, variant_id)
    assert s.quantity == 10 and s.reserved == 0

    cust = await test_db.get(Customer, _uuid.UUID(customer_id))
    await test_db.refresh(cust)
    assert cust.current_debt == Decimal("0")


async def test_cancel_shipped_returns_stock(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 3)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(f"/api/v1/orders/{order['id']}/ship", headers=admin_headers)

    r = await client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Nuqson"},
    )
    assert r.status_code == 200
    s = await _stock(test_db, variant_id)
    # 10 - 3 (ship) + 3 (cancel-after-ship) = 10
    assert s.quantity == 10


async def test_cannot_cancel_completed(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 1)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(
        f"/api/v1/orders/{order['id']}/pay", headers=admin_headers, json={"amount": "10000"}
    )
    await client.post(f"/api/v1/orders/{order['id']}/ship", headers=admin_headers)

    # Endi COMPLETED
    r = await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=admin_headers, json={})
    assert r.status_code == 400


# ============ Invoice + Celery ============


async def test_invoice_create_sends_celery_task(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    sent: list[tuple] = []

    def _fake(name, args=None, **kw):
        sent.append((name, args))
        return type("X", (), {"id": "fake"})()

    from app.api.v1.sales import orders as orders_module

    monkeypatch.setattr(orders_module.celery_app, "send_task", _fake)

    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 2)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)

    r = await client.post(f"/api/v1/orders/{order['id']}/invoices", headers=admin_headers)
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["status"] == "pending"
    assert inv["number"].startswith("INV-")
    assert Decimal(inv["total"]) == Decimal("20000")

    assert len(sent) == 1
    name, args = sent[0]
    assert name == "generate_invoice_pdf" and args == [inv["id"]]


async def test_invoice_for_draft_400(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 1)
    r = await client.post(f"/api/v1/orders/{order['id']}/invoices", headers=admin_headers)
    assert r.status_code == 400


# ============ Returns ============


async def test_return_request_and_approve_restores_stock(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
    test_db: AsyncSession,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 5)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_headers,
        json={"amount": "50000"},
    )
    await client.post(f"/api/v1/orders/{order['id']}/ship", headers=admin_headers)

    # Endi COMPLETED. Stock = 5
    s = await _stock(test_db, variant_id)
    assert s.quantity == 5

    # 2 ta qaytarish
    items = order["items"]
    r = await client.post(
        "/api/v1/returns",
        headers=admin_headers,
        json={
            "order_id": order["id"],
            "items": [{"order_item_id": items[0]["id"], "quantity": 2}],
            "reason": "Yoqmadi",
        },
    )
    assert r.status_code == 201, r.text
    ret = r.json()
    assert ret["status"] == "requested"
    assert Decimal(ret["total_refund"]) == Decimal("20000")

    # Approve — stock + balans
    ap = await client.post(f"/api/v1/returns/{ret['id']}/approve", headers=admin_headers)
    assert ap.status_code == 200
    assert ap.json()["status"] == "approved"

    s = await _stock(test_db, variant_id)
    assert s.quantity == 7  # 5 + 2


async def test_return_for_draft_order_400(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 1)
    items = order["items"]
    r = await client.post(
        "/api/v1/returns",
        headers=admin_headers,
        json={
            "order_id": order["id"],
            "items": [{"order_item_id": items[0]["id"], "quantity": 1}],
        },
    )
    assert r.status_code == 400


async def test_return_qty_exceeds_order_item_400(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    order = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 3)
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(f"/api/v1/orders/{order['id']}/ship", headers=admin_headers)

    items = order["items"]
    r = await client.post(
        "/api/v1/returns",
        headers=admin_headers,
        json={
            "order_id": order["id"],
            "items": [{"order_item_id": items[0]["id"], "quantity": 100}],
        },
    )
    assert r.status_code == 400


# ============ List + filter ============


async def test_orders_filter_by_status_and_customer(
    client: AsyncClient,
    admin_headers: dict[str, str],
    catalog_setup: tuple[str, str],
    warehouse_id: str,
    customer_id: str,
) -> None:
    _, variant_id = catalog_setup
    await _stock_in(client, admin_headers, variant_id, warehouse_id, 10)
    # 2 draft, 1 confirmed
    for qty in [1, 1]:
        await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, qty)
    confirmed = await _create_order(client, admin_headers, customer_id, warehouse_id, variant_id, 1)
    await client.post(f"/api/v1/orders/{confirmed['id']}/confirm", headers=admin_headers)

    drafts = await client.get("/api/v1/orders", headers=admin_headers, params={"status": "draft"})
    assert drafts.json()["total"] == 2
    by_cust = await client.get(
        "/api/v1/orders", headers=admin_headers, params={"customer_id": customer_id}
    )
    assert by_cust.json()["total"] == 3
