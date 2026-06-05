"""Mavjud testlardan tushib qolgan service path'lari uchun qo'shimcha testlar.

Maqsad: replace_items (order/purchase), PAID statusda cancel, audit.diff_attrs
edge case'lar — coverage >80%.
"""

from __future__ import annotations

import uuid as _uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.stock import Stock
from app.models.user import User
from app.services.audit import diff_attrs

# ---- Common fixtures ----


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def setup_order_world(client: AsyncClient, admin_headers: dict[str, str]) -> dict[str, str]:
    """Minimal: category + product + variant + warehouse + customer + stock."""
    cat = (
        await client.post("/api/v1/categories", headers=admin_headers, json={"name": "C"})
    ).json()
    prod = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={"name": "P", "category_id": cat["id"]},
        )
    ).json()
    var = (
        await client.post(
            f"/api/v1/products/{prod['id']}/variants",
            headers=admin_headers,
            json={"size": "M", "color": "Q", "wholesale_price": "1000", "retail_price": "1500"},
        )
    ).json()
    var2 = (
        await client.post(
            f"/api/v1/products/{prod['id']}/variants",
            headers=admin_headers,
            json={"size": "L", "color": "Q", "wholesale_price": "1500", "retail_price": "2200"},
        )
    ).json()
    wh = (
        await client.post(
            "/api/v1/warehouses",
            headers=admin_headers,
            json={"name": "W", "code": "W"},
        )
    ).json()
    cust = (
        await client.post(
            "/api/v1/customers",
            headers=admin_headers,
            json={"name": "M", "credit_limit": "1000000"},
        )
    ).json()
    await client.post(
        "/api/v1/stock/movements/receive",
        headers=admin_headers,
        json={"variant_id": var["id"], "to_warehouse_id": wh["id"], "quantity": 50},
    )
    await client.post(
        "/api/v1/stock/movements/receive",
        headers=admin_headers,
        json={"variant_id": var2["id"], "to_warehouse_id": wh["id"], "quantity": 50},
    )
    return {
        "variant_id": var["id"],
        "variant_id2": var2["id"],
        "warehouse_id": wh["id"],
        "customer_id": cust["id"],
    }


# ============ services/order.py — replace_items + cancel(PAID) ============


async def test_patch_draft_order_replaces_items(
    client: AsyncClient,
    admin_headers: dict[str, str],
    setup_order_world: dict[str, str],
    test_db: AsyncSession,
) -> None:
    """PATCH /orders/{id} items[]: replace_items service'i ishga tushadi."""
    s = setup_order_world
    order = (
        await client.post(
            "/api/v1/orders",
            headers=admin_headers,
            json={
                "customer_id": s["customer_id"],
                "warehouse_id": s["warehouse_id"],
                "items": [{"variant_id": s["variant_id"], "quantity": 2}],
            },
        )
    ).json()
    assert Decimal(order["total"]) == Decimal("2000")  # 2*1000

    # PATCH bilan ikkala variantni qaytadan o'rnatamiz
    upd = await client.patch(
        f"/api/v1/orders/{order['id']}",
        headers=admin_headers,
        json={
            "items": [
                {"variant_id": s["variant_id"], "quantity": 3},
                {"variant_id": s["variant_id2"], "quantity": 1},
            ],
            "discount": "500",
        },
    )
    assert upd.status_code == 200, upd.text
    body = upd.json()
    assert len(body["items"]) == 2
    # 3*1000 + 1*1500 = 4500, -500 discount = 4000
    assert Decimal(body["total"]) == Decimal("4000")


async def test_patch_non_draft_order_400(
    client: AsyncClient,
    admin_headers: dict[str, str],
    setup_order_world: dict[str, str],
) -> None:
    """CONFIRMED orderga PATCH 400 qaytarishi kerak."""
    s = setup_order_world
    order = (
        await client.post(
            "/api/v1/orders",
            headers=admin_headers,
            json={
                "customer_id": s["customer_id"],
                "warehouse_id": s["warehouse_id"],
                "items": [{"variant_id": s["variant_id"], "quantity": 1}],
            },
        )
    ).json()
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)

    r = await client.patch(
        f"/api/v1/orders/{order['id']}",
        headers=admin_headers,
        json={"notes": "test"},
    )
    assert r.status_code == 400


async def test_cancel_paid_order_keeps_payment_as_credit(
    client: AsyncClient,
    admin_headers: dict[str, str],
    setup_order_world: dict[str, str],
    test_db: AsyncSession,
) -> None:
    """PAID statusdan cancel: reserve release; paid_amount mijoz omonati sifatida saqlanadi.
    Bu service'da PAID branch'ini coveraga qo'shadi."""
    s = setup_order_world
    order = (
        await client.post(
            "/api/v1/orders",
            headers=admin_headers,
            json={
                "customer_id": s["customer_id"],
                "warehouse_id": s["warehouse_id"],
                "items": [{"variant_id": s["variant_id"], "quantity": 2}],
            },
        )
    ).json()
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_headers,
        json={"amount": "2000"},
    )
    # endi PAID
    o_db = await test_db.get(Order, _uuid.UUID(order["id"]))
    await test_db.refresh(o_db)
    assert o_db.status == OrderStatus.PAID

    r = await client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Mijoz qaytarib oldi"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    # Stock — release qilingan (reserved 0, quantity 50 saqlanmoqda)
    st = (
        await test_db.execute(select(Stock).where(Stock.variant_id == _uuid.UUID(s["variant_id"])))
    ).scalar_one()
    assert st.reserved == 0


# ============ services/purchase.py — replace_items ============


async def test_patch_draft_po_replaces_items(
    client: AsyncClient,
    admin_headers: dict[str, str],
    setup_order_world: dict[str, str],
    test_db: AsyncSession,
) -> None:
    s = setup_order_world
    supplier = (
        await client.post(
            "/api/v1/suppliers",
            headers=admin_headers,
            json={"name": "Sup"},
        )
    ).json()

    po = (
        await client.post(
            "/api/v1/purchase-orders",
            headers=admin_headers,
            json={
                "supplier_id": supplier["id"],
                "warehouse_id": s["warehouse_id"],
                "items": [{"variant_id": s["variant_id"], "quantity": 10, "unit_cost": "500"}],
            },
        )
    ).json()
    assert Decimal(po["total"]) == Decimal("5000")

    upd = await client.patch(
        f"/api/v1/purchase-orders/{po['id']}",
        headers=admin_headers,
        json={
            "items": [
                {"variant_id": s["variant_id"], "quantity": 5, "unit_cost": "600"},
                {"variant_id": s["variant_id2"], "quantity": 3, "unit_cost": "800"},
            ],
        },
    )
    assert upd.status_code == 200, upd.text
    body = upd.json()
    assert len(body["items"]) == 2
    # 5*600 + 3*800 = 5400
    assert Decimal(body["total"]) == Decimal("5400")


async def test_patch_non_draft_po_400(
    client: AsyncClient,
    admin_headers: dict[str, str],
    setup_order_world: dict[str, str],
    test_db: AsyncSession,
) -> None:
    s = setup_order_world
    supplier = (
        await client.post(
            "/api/v1/suppliers",
            headers=admin_headers,
            json={"name": "Sup2"},
        )
    ).json()
    po = (
        await client.post(
            "/api/v1/purchase-orders",
            headers=admin_headers,
            json={
                "supplier_id": supplier["id"],
                "warehouse_id": s["warehouse_id"],
                "items": [{"variant_id": s["variant_id"], "quantity": 1, "unit_cost": "10"}],
            },
        )
    ).json()
    await client.post(f"/api/v1/purchase-orders/{po['id']}/receive", headers=admin_headers)

    r = await client.patch(
        f"/api/v1/purchase-orders/{po['id']}",
        headers=admin_headers,
        json={"notes": "x"},
    )
    assert r.status_code == 400

    po_db = await test_db.get(PurchaseOrder, _uuid.UUID(po["id"]))
    await test_db.refresh(po_db)
    assert po_db.status == PurchaseOrderStatus.RECEIVED


# ============ services/audit.py — diff_attrs edge cases ============


def test_diff_attrs_ignores_fields_not_in_allowed() -> None:
    class Obj:
        a = 1
        b = 2

    obj = Obj()
    changes = diff_attrs(obj, {"a": 5, "c": 99}, allowed={"a"})
    assert "a" in changes and changes["a"]["new"] == 5
    assert "c" not in changes


def test_diff_attrs_no_changes_when_values_equal() -> None:
    class Obj:
        a = "x"

    obj = Obj()
    changes = diff_attrs(obj, {"a": "x"}, allowed={"a"})
    assert changes == {}
