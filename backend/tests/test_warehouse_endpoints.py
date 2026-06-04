"""Ombor moduli: warehouse CRUD, stock list, movements (receive/issue/transfer/reserve/release),
low-stock notify, inventory finalize."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User


# ---- Common fixtures ----

@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def sales_headers(client: AsyncClient, sales_user: User) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "SalesPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def catalog_setup(
    client: AsyncClient, admin_headers: dict[str, str]
) -> tuple[str, str, str]:
    """Kategoriya + brend + mahsulot + 1 variant — keyingi testlarda ishlatish uchun."""
    cat = (await client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "Maykalar"}
    )).json()
    brand = (await client.post(
        "/api/v1/brands", headers=admin_headers, json={"name": "Nike"}
    )).json()
    prod = (await client.post(
        "/api/v1/products", headers=admin_headers,
        json={"name": "Mayka", "category_id": cat["id"], "brand_id": brand["id"]},
    )).json()
    variant = (await client.post(
        f"/api/v1/products/{prod['id']}/variants", headers=admin_headers,
        json={"size": "M", "color": "Qora", "wholesale_price": "100000", "retail_price": "150000"},
    )).json()
    return cat["id"], prod["id"], variant["id"]


@pytest.fixture
async def two_warehouses(
    client: AsyncClient, admin_headers: dict[str, str]
) -> tuple[str, str]:
    a = (await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "Markaz", "code": "MAIN", "type": "main"},
    )).json()
    b = (await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "Filial", "code": "BRA01", "type": "branch"},
    )).json()
    return a["id"], b["id"]


# ============ Warehouses CRUD ============

async def test_warehouse_create_with_type(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "Asosiy", "code": "W1", "type": "main"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "main" and body["code"] == "W1"


async def test_warehouse_filter_by_type(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    for code, typ in [("M1", "main"), ("B1", "branch"), ("B2", "branch")]:
        await client.post(
            "/api/v1/warehouses", headers=admin_headers,
            json={"name": code, "code": code, "type": typ},
        )
    r = await client.get(
        "/api/v1/warehouses", headers=admin_headers, params={"type": "branch"}
    )
    assert r.json()["total"] == 2


async def test_warehouse_code_unique_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "A", "code": "DUP"},
    )
    dup = await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "B", "code": "DUP"},
    )
    assert dup.status_code == 409


async def test_sales_user_cannot_write_warehouse(
    client: AsyncClient, sales_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/warehouses", headers=sales_headers,
        json={"name": "X", "code": "X"},
    )
    assert r.status_code == 403


# ============ Stock & movements ============

async def _receive(client, headers, variant, warehouse, qty, **kw):
    return await client.post(
        "/api/v1/stock/movements/receive", headers=headers,
        json={"variant_id": variant, "to_warehouse_id": warehouse, "quantity": qty, **kw},
    )


async def _issue(client, headers, variant, warehouse, qty):
    return await client.post(
        "/api/v1/stock/movements/issue", headers=headers,
        json={"variant_id": variant, "from_warehouse_id": warehouse, "quantity": qty},
    )


async def _transfer(client, headers, variant, from_wh, to_wh, qty):
    return await client.post(
        "/api/v1/stock/movements/transfer", headers=headers,
        json={"variant_id": variant, "from_warehouse_id": from_wh,
              "to_warehouse_id": to_wh, "quantity": qty},
    )


async def _reserve(client, headers, variant, warehouse, qty):
    return await client.post(
        "/api/v1/stock/movements/reserve", headers=headers,
        json={"variant_id": variant, "warehouse_id": warehouse, "quantity": qty},
    )


async def _release(client, headers, variant, warehouse, qty):
    return await client.post(
        "/api/v1/stock/movements/release", headers=headers,
        json={"variant_id": variant, "warehouse_id": warehouse, "quantity": qty},
    )


async def test_receive_creates_stock_and_movement(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
    test_db: AsyncSession,
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses

    r = await _receive(client, admin_headers, variant_id, a, 100)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "in" and body["quantity"] == 100
    assert body["to_warehouse_id"] == a

    listed = await client.get(
        "/api/v1/stock", headers=admin_headers,
        params={"warehouse_id": a, "variant_id": variant_id},
    )
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 100 and items[0]["available"] == 100


async def test_issue_decrements_and_logs(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 50)

    r = await _issue(client, admin_headers, variant_id, a, 20)
    assert r.status_code == 201

    listed = await client.get(
        "/api/v1/stock", headers=admin_headers, params={"warehouse_id": a}
    )
    assert listed.json()["items"][0]["quantity"] == 30


async def test_issue_insufficient_409_and_no_change(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 10)

    r = await _issue(client, admin_headers, variant_id, a, 50)
    assert r.status_code == 409
    assert "yetarli qoldiq" in r.json()["detail"].lower()

    # qoldiq o'zgarmagan
    listed = await client.get(
        "/api/v1/stock", headers=admin_headers, params={"warehouse_id": a}
    )
    assert listed.json()["items"][0]["quantity"] == 10


async def test_transfer_atomic_between_warehouses(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
    test_db: AsyncSession,
) -> None:
    _, _, variant_id = catalog_setup
    a, b = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 30)

    r = await _transfer(client, admin_headers, variant_id, a, b, 10)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "transfer"
    assert body["from_warehouse_id"] == a and body["to_warehouse_id"] == b

    # Ikkalasini ham tekshiramiz: a=20, b=10
    stocks = (
        await test_db.execute(
            select(Stock).where(Stock.variant_id == uuid.UUID(variant_id))
        )
    ).scalars().all()
    by_wh = {str(s.warehouse_id): s.quantity for s in stocks}
    assert by_wh[a] == 20 and by_wh[b] == 10

    # Bitta TRANSFER movement bo'lishi kerak (atomik)
    movements = (
        await test_db.execute(
            select(StockMovement).where(StockMovement.type == MovementType.TRANSFER)
        )
    ).scalars().all()
    assert len(movements) == 1
    assert movements[0].quantity == 10


async def test_transfer_insufficient_rollback(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
    test_db: AsyncSession,
) -> None:
    _, _, variant_id = catalog_setup
    a, b = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 5)

    r = await _transfer(client, admin_headers, variant_id, a, b, 100)
    assert r.status_code == 409

    # a hali ham 5, b da Stock yo'q (atomik rollback)
    rows = (
        await test_db.execute(
            select(Stock).where(Stock.variant_id == uuid.UUID(variant_id))
        )
    ).scalars().all()
    by_wh = {str(s.warehouse_id): s.quantity for s in rows}
    assert by_wh[a] == 5
    assert b not in by_wh


async def test_transfer_same_warehouse_400(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 10)
    r = await _transfer(client, admin_headers, variant_id, a, a, 5)
    assert r.status_code == 400


# ============ Reservations ============

async def test_reserve_reduces_available_but_not_quantity(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 20)

    r = await _reserve(client, admin_headers, variant_id, a, 7)
    assert r.status_code == 201

    listed = await client.get(
        "/api/v1/stock", headers=admin_headers, params={"warehouse_id": a}
    )
    item = listed.json()["items"][0]
    assert item["quantity"] == 20 and item["reserved"] == 7 and item["available"] == 13


async def test_reserve_more_than_available_409(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 5)
    r = await _reserve(client, admin_headers, variant_id, a, 10)
    assert r.status_code == 409


async def test_release_restores_available(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 20)
    await _reserve(client, admin_headers, variant_id, a, 10)

    r = await _release(client, admin_headers, variant_id, a, 4)
    assert r.status_code == 201

    listed = await client.get(
        "/api/v1/stock", headers=admin_headers, params={"warehouse_id": a}
    )
    item = listed.json()["items"][0]
    assert item["reserved"] == 6 and item["available"] == 14


async def test_release_more_than_reserved_400(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 10)
    await _reserve(client, admin_headers, variant_id, a, 3)

    r = await _release(client, admin_headers, variant_id, a, 10)
    assert r.status_code == 400


# ============ Low-stock notification ============

async def test_issue_below_min_triggers_celery_notify(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
    test_db: AsyncSession,
) -> None:
    sent: list[tuple] = []

    def _fake_send_task(name: str, args=None, **kwargs):
        sent.append((name, args))
        return type("Async", (), {"id": "fake"})()

    from app.tasks import celery_app as celery_module
    monkeypatch.setattr(celery_module.celery_app, "send_task", _fake_send_task)

    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 20)

    # min_quantity = 10 belgilaymiz
    stock = (
        await test_db.execute(
            select(Stock).where(Stock.variant_id == uuid.UUID(variant_id))
        )
    ).scalar_one()
    upd = await client.patch(
        f"/api/v1/stock/{stock.id}/min",
        headers=admin_headers, json={"min_quantity": 10},
    )
    assert upd.status_code == 200

    # 20 -> 15 (hali ham 15 >= 10) — notify YO'Q
    await _issue(client, admin_headers, variant_id, a, 5)
    assert sent == []

    # 15 -> 5 (5 < 10) — notify chaqirilishi kerak
    await _issue(client, admin_headers, variant_id, a, 10)
    assert len(sent) == 1
    name, args = sent[0]
    assert name == "notify_low_stock"
    assert args[3] == 5 and args[4] == 10  # available, min_quantity


# ============ Inventory ============

async def test_inventory_session_count_and_finalize(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
    test_db: AsyncSession,
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 50)

    inv = (await client.post(
        "/api/v1/inventory", headers=admin_headers,
        json={"warehouse_id": a, "notes": "Oylik inventarizatsiya"},
    )).json()
    assert inv["status"] == "in_progress"

    # Sanab chiqdik: faktik 47 (3 ta yetishmaydi)
    r = await client.post(
        f"/api/v1/inventory/{inv['id']}/items", headers=admin_headers,
        json={"variant_id": variant_id, "counted_quantity": 47},
    )
    assert r.status_code == 201
    item = next(i for i in r.json()["items"] if i["variant_id"] == variant_id)
    assert item["expected_quantity"] == 50
    assert item["counted_quantity"] == 47
    assert item["difference"] == -3

    fin = await client.post(
        f"/api/v1/inventory/{inv['id']}/finalize", headers=admin_headers
    )
    assert fin.status_code == 200
    assert fin.json()["adjustments"] == 1
    assert fin.json()["status"] == "completed"

    # Stock 47 ga tushgan
    stocks = (
        await test_db.execute(
            select(Stock).where(Stock.variant_id == uuid.UUID(variant_id))
        )
    ).scalars().all()
    assert stocks[0].quantity == 47

    # ADJUST movement yozilgan
    movs = (
        await test_db.execute(
            select(StockMovement).where(StockMovement.type == MovementType.ADJUST)
        )
    ).scalars().all()
    assert len(movs) == 1 and movs[0].quantity == 3


async def test_inventory_cannot_count_after_finalize(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, _ = two_warehouses
    inv = (await client.post(
        "/api/v1/inventory", headers=admin_headers, json={"warehouse_id": a}
    )).json()
    await client.post(
        f"/api/v1/inventory/{inv['id']}/finalize", headers=admin_headers
    )
    r = await client.post(
        f"/api/v1/inventory/{inv['id']}/items", headers=admin_headers,
        json={"variant_id": variant_id, "counted_quantity": 5},
    )
    assert r.status_code == 400


# ============ History endpoint ============

async def test_movements_history_filter_by_type(
    client: AsyncClient, admin_headers: dict[str, str],
    catalog_setup: tuple[str, str, str], two_warehouses: tuple[str, str],
) -> None:
    _, _, variant_id = catalog_setup
    a, b = two_warehouses
    await _receive(client, admin_headers, variant_id, a, 30)
    await _issue(client, admin_headers, variant_id, a, 5)
    await _transfer(client, admin_headers, variant_id, a, b, 10)

    r = await client.get(
        "/api/v1/stock/movements", headers=admin_headers, params={"type": "in"}
    )
    assert r.json()["total"] == 1

    r = await client.get(
        "/api/v1/stock/movements", headers=admin_headers, params={"warehouse_id": b}
    )
    # b da faqat TRANSFER (to_warehouse)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["type"] == "transfer"
