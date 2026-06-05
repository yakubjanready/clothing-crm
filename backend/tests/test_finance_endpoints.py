"""Moliya moduli: /accounts, /payments (+ /transfer), /debts + DebtRecord avtomatik yozuv."""
from __future__ import annotations

import uuid as _uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.customer import Customer
from app.models.debt_record import DebtDirection, DebtPartyType, DebtRecord
from app.models.finance_payment import FinanceCategory, PaymentDirection
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


async def _create_account(client, headers, name, type_="cash", initial="0"):
    return (await client.post(
        "/api/v1/accounts", headers=headers,
        json={"name": name, "type": type_, "initial_balance": initial},
    )).json()


# ============ Account CRUD ============

async def test_create_account_with_initial_balance(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/accounts", headers=admin_headers,
        json={
            "name": "Asosiy kassa", "code": "CASH-01",
            "type": "cash", "initial_balance": "500000",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Asosiy kassa"
    assert body["type"] == "cash"
    assert Decimal(body["balance"]) == Decimal("500000")


async def test_account_name_unique_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _create_account(client, admin_headers, "Dup")
    r = await client.post(
        "/api/v1/accounts", headers=admin_headers, json={"name": "Dup"}
    )
    assert r.status_code == 409


async def test_account_filter_by_type(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _create_account(client, admin_headers, "Kassa", "cash")
    await _create_account(client, admin_headers, "Bank Asia", "bank")
    await _create_account(client, admin_headers, "Bank Saderat", "bank")

    r = await client.get(
        "/api/v1/accounts", headers=admin_headers, params={"type": "bank"}
    )
    assert r.json()["total"] == 2


async def test_account_cannot_delete_with_balance(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    a = await _create_account(client, admin_headers, "Cash", initial="100")
    r = await client.delete(f"/api/v1/accounts/{a['id']}", headers=admin_headers)
    assert r.status_code == 400
    assert "Balans nol" in r.json()["detail"]


async def test_sales_user_cannot_write_account(
    client: AsyncClient, sales_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/accounts", headers=sales_headers,
        json={"name": "X"},
    )
    assert r.status_code == 403


# ============ Income / Expense ============

async def test_income_payment_increases_balance(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="1000")

    r = await client.post(
        "/api/v1/payments", headers=admin_headers,
        json={
            "direction": "income", "category": "customer_payment",
            "account_id": a["id"], "amount": "5000",
            "description": "Mijoz to'lovi",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["category"] == "customer_payment"

    acc = await test_db.get(Account, _uuid.UUID(a["id"]))
    await test_db.refresh(acc)
    assert acc.balance == Decimal("6000")


async def test_expense_payment_decreases_balance(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="10000")

    r = await client.post(
        "/api/v1/payments", headers=admin_headers,
        json={
            "direction": "expense", "category": "expense",
            "account_id": a["id"], "amount": "3000",
            "description": "Ofis ijara",
        },
    )
    assert r.status_code == 201

    acc = await test_db.get(Account, _uuid.UUID(a["id"]))
    await test_db.refresh(acc)
    assert acc.balance == Decimal("7000")


async def test_expense_insufficient_funds_409(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="100")
    r = await client.post(
        "/api/v1/payments", headers=admin_headers,
        json={
            "direction": "expense", "category": "expense",
            "account_id": a["id"], "amount": "5000",
        },
    )
    assert r.status_code == 409
    assert "yetarli mablag" in r.json()["detail"].lower()

    # Balans o'zgarmaganini tasdiqlash
    acc = await test_db.get(Account, _uuid.UUID(a["id"]))
    await test_db.refresh(acc)
    assert acc.balance == Decimal("100")


async def test_create_payment_with_transfer_category_rejected(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="100")
    r = await client.post(
        "/api/v1/payments", headers=admin_headers,
        json={
            "direction": "expense", "category": "transfer",
            "account_id": a["id"], "amount": "50",
        },
    )
    assert r.status_code == 400
    assert "transfer" in r.json()["detail"].lower()


# ============ Transfer ============

async def test_transfer_atomic_between_accounts(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", "cash", initial="10000")
    b = await _create_account(client, admin_headers, "Bank", "bank", initial="500")

    r = await client.post(
        "/api/v1/payments/transfer", headers=admin_headers,
        json={"from_account_id": a["id"], "to_account_id": b["id"],
              "amount": "3000", "description": "Kassadan bankka"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["out_payment"]["direction"] == "expense"
    assert body["in_payment"]["direction"] == "income"
    assert body["out_payment"]["category"] == "transfer"
    assert body["in_payment"]["related_account_id"] == a["id"]

    acc_a = await test_db.get(Account, _uuid.UUID(a["id"]))
    acc_b = await test_db.get(Account, _uuid.UUID(b["id"]))
    await test_db.refresh(acc_a); await test_db.refresh(acc_b)
    assert acc_a.balance == Decimal("7000")
    assert acc_b.balance == Decimal("3500")


async def test_transfer_insufficient_funds_409(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="100")
    b = await _create_account(client, admin_headers, "Bank", "bank")

    r = await client.post(
        "/api/v1/payments/transfer", headers=admin_headers,
        json={"from_account_id": a["id"], "to_account_id": b["id"], "amount": "1000"},
    )
    assert r.status_code == 409

    # Hech narsa o'zgarmagan
    acc_a = await test_db.get(Account, _uuid.UUID(a["id"]))
    await test_db.refresh(acc_a)
    assert acc_a.balance == Decimal("100")


async def test_transfer_same_account_400(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="1000")
    r = await client.post(
        "/api/v1/payments/transfer", headers=admin_headers,
        json={"from_account_id": a["id"], "to_account_id": a["id"], "amount": "10"},
    )
    assert r.status_code == 400


# ============ Payments list/filter ============

async def test_payments_filter_by_direction_and_account(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    a = await _create_account(client, admin_headers, "Kassa", initial="10000")
    # 2 ta income, 1 ta expense
    for d, amt in [("income", "1000"), ("income", "500"), ("expense", "200")]:
        await client.post(
            "/api/v1/payments", headers=admin_headers,
            json={"direction": d, "category": "other",
                  "account_id": a["id"], "amount": amt},
        )

    incomes = await client.get(
        "/api/v1/payments", headers=admin_headers, params={"direction": "income"}
    )
    assert incomes.json()["total"] == 2

    by_acc = await client.get(
        "/api/v1/payments", headers=admin_headers, params={"account_id": a["id"]}
    )
    assert by_acc.json()["total"] == 3


# ============ DebtRecord auto-write ============

async def test_debt_record_written_on_customer_confirm_order(
    client: AsyncClient, admin_headers: dict[str, str],
    test_db: AsyncSession,
) -> None:
    """Buyurtma confirm qilinganda customer.current_debt += order.total va
    DebtRecord avtomatik yoziladi."""
    # Setup
    cat = (await client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "Mayka"}
    )).json()
    prod = (await client.post(
        "/api/v1/products", headers=admin_headers,
        json={"name": "K", "category_id": cat["id"]},
    )).json()
    var = (await client.post(
        f"/api/v1/products/{prod['id']}/variants", headers=admin_headers,
        json={"size": "M", "color": "Qora",
              "wholesale_price": "10000", "retail_price": "15000"},
    )).json()
    wh = (await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "Main", "code": "M"},
    )).json()
    cust = (await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "Mijoz", "credit_limit": "1000000"},
    )).json()
    await client.post(
        "/api/v1/stock/movements/receive", headers=admin_headers,
        json={"variant_id": var["id"], "to_warehouse_id": wh["id"], "quantity": 10},
    )
    order = (await client.post(
        "/api/v1/orders", headers=admin_headers,
        json={
            "customer_id": cust["id"], "warehouse_id": wh["id"],
            "items": [{"variant_id": var["id"], "quantity": 5}],
        },
    )).json()

    # Confirm — debt += 50000, DebtRecord yozilishi kerak
    await client.post(
        f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers
    )

    records = (await test_db.execute(
        select(DebtRecord).where(
            DebtRecord.party_type == DebtPartyType.CUSTOMER,
            DebtRecord.party_id == _uuid.UUID(cust["id"]),
        )
    )).scalars().all()
    assert len(records) == 1
    assert records[0].direction == DebtDirection.INCREASE
    assert records[0].amount == Decimal("50000")
    assert records[0].balance_after == Decimal("50000")


async def test_debt_record_for_pay_decreases(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    """Order pay qilinganda DECREASE yozuvi."""
    # Setup minimal flow
    cat = (await client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "C"}
    )).json()
    prod = (await client.post(
        "/api/v1/products", headers=admin_headers,
        json={"name": "P", "category_id": cat["id"]},
    )).json()
    var = (await client.post(
        f"/api/v1/products/{prod['id']}/variants", headers=admin_headers,
        json={"size": "M", "color": "Q", "wholesale_price": "1000", "retail_price": "1500"},
    )).json()
    wh = (await client.post(
        "/api/v1/warehouses", headers=admin_headers, json={"name": "W", "code": "W"},
    )).json()
    cust = (await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "M", "credit_limit": "100000"},
    )).json()
    await client.post(
        "/api/v1/stock/movements/receive", headers=admin_headers,
        json={"variant_id": var["id"], "to_warehouse_id": wh["id"], "quantity": 5},
    )
    order = (await client.post(
        "/api/v1/orders", headers=admin_headers,
        json={"customer_id": cust["id"], "warehouse_id": wh["id"],
              "items": [{"variant_id": var["id"], "quantity": 5}]},
    )).json()
    await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=admin_headers)
    # debt = 5000 endi

    await client.post(
        f"/api/v1/orders/{order['id']}/pay", headers=admin_headers,
        json={"amount": "5000"},
    )

    # Confirmda INCREASE + Pay'da DECREASE
    records = (await test_db.execute(
        select(DebtRecord)
        .where(DebtRecord.party_id == _uuid.UUID(cust["id"]))
        .order_by(DebtRecord.created_at)
    )).scalars().all()
    assert len(records) == 2
    assert records[0].direction == DebtDirection.INCREASE
    assert records[1].direction == DebtDirection.DECREASE
    assert records[1].balance_after == Decimal("0")


async def test_debts_endpoint_filter_by_party_type(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    """/debts endpoint filter ishlatadi."""
    # Direct customer add (qisqartirilgan flow)
    cust = Customer(name="X", credit_limit=Decimal("10000"), current_debt=Decimal("0"))
    test_db.add(cust)
    await test_db.commit()

    # Bevosita adjust orqali (service test)
    from app.services.customer import adjust_customer_debt
    await adjust_customer_debt(test_db, customer=cust, delta=Decimal("1000"))
    await adjust_customer_debt(test_db, customer=cust, delta=Decimal("-500"))
    await test_db.commit()

    customers = await client.get(
        "/api/v1/debts", headers=admin_headers, params={"party_type": "customer"}
    )
    assert customers.json()["total"] == 2

    # Bittasi increase, bittasi decrease
    increases = await client.get(
        "/api/v1/debts", headers=admin_headers,
        params={"party_type": "customer", "direction": "increase"},
    )
    assert increases.json()["total"] == 1
