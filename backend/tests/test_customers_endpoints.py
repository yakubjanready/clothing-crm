"""Mijozlar moduli: CRUD+filter, kontaktlar, interactions, balance, kredit limit."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerSegment, PriceType
from app.models.user import User
from app.services.customer import (
    CreditLimitExceededError,
    adjust_customer_debt,
    check_credit_limit,
)


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


# ============ services/customer.py — pure ============

def test_check_credit_limit_passes_within_limit() -> None:
    c = Customer(
        name="X", credit_limit=Decimal("1000"), current_debt=Decimal("200"),
    )
    check_credit_limit(c, Decimal("500"))  # 200+500=700 < 1000 — ok


def test_check_credit_limit_passes_for_payment_or_zero() -> None:
    c = Customer(
        name="X", credit_limit=Decimal("100"), current_debt=Decimal("150"),
    )
    # additional_debt <= 0 — limit ahamiyatsiz
    check_credit_limit(c, Decimal("0"))
    check_credit_limit(c, Decimal("-50"))


def test_check_credit_limit_zero_means_no_credit() -> None:
    c = Customer(
        name="X", credit_limit=Decimal("0"), current_debt=Decimal("0"),
    )
    with pytest.raises(CreditLimitExceededError):
        check_credit_limit(c, Decimal("1"))


def test_check_credit_limit_exceeds_raises() -> None:
    c = Customer(
        name="X", credit_limit=Decimal("100"), current_debt=Decimal("80"),
    )
    with pytest.raises(CreditLimitExceededError) as exc:
        check_credit_limit(c, Decimal("50"))
    assert "oshib ketgan" in str(exc.value)


async def test_adjust_customer_debt_clamps_to_zero(test_db: AsyncSession) -> None:
    c = Customer(
        name="X", credit_limit=Decimal("500"), current_debt=Decimal("100"),
    )
    test_db.add(c)
    await test_db.commit()

    # over-payment — 0 ga to'xtaydi
    await adjust_customer_debt(test_db, customer=c, delta=Decimal("-300"))
    assert c.current_debt == Decimal("0")


async def test_adjust_customer_debt_blocks_when_over_limit(
    test_db: AsyncSession,
) -> None:
    c = Customer(
        name="X", credit_limit=Decimal("100"), current_debt=Decimal("50"),
    )
    test_db.add(c)
    await test_db.commit()
    with pytest.raises(CreditLimitExceededError):
        await adjust_customer_debt(test_db, customer=c, delta=Decimal("100"))


# ============ Customer CRUD ============

async def test_create_customer_with_defaults(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "Olamtekstil LLC", "inn": "301234567"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Olamtekstil LLC"
    assert body["segment"] == CustomerSegment.NEW
    assert body["price_type"] == PriceType.WHOLESALE
    assert Decimal(body["credit_limit"]) == Decimal("0")
    assert Decimal(body["current_debt"]) == Decimal("0")


async def test_create_customer_with_segment_and_credit_limit(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={
            "name": "Vip Mijoz",
            "segment": "vip",
            "price_type": "special",
            "credit_limit": "10000000",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["segment"] == "vip"
    assert Decimal(body["credit_limit"]) == Decimal("10000000")


async def test_inn_unique_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "A", "inn": "DUP123"},
    )
    dup = await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "B", "inn": "DUP123"},
    )
    assert dup.status_code == 409


async def test_customer_filter_by_segment_and_search(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    for n, s in [("Toshkent Savdo", "vip"), ("Andijon Savdo", "regular"), ("Yangi Mijoz", "new")]:
        await client.post(
            "/api/v1/customers", headers=admin_headers,
            json={"name": n, "segment": s},
        )
    vips = await client.get(
        "/api/v1/customers", headers=admin_headers, params={"segment": "vip"}
    )
    assert vips.json()["total"] == 1

    savdo = await client.get(
        "/api/v1/customers", headers=admin_headers, params={"search": "savdo"}
    )
    assert savdo.json()["total"] == 2


async def test_customer_filter_has_debt_and_over_limit(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    # 3 ta mijoz: nol qarz, 500 qarz (limit 1000), 200 qarz (limit 100 — over)
    for n, lim, debt in [("nol", "1000", "0"), ("middle", "1000", "500"), ("over", "100", "200")]:
        c = Customer(
            name=n, credit_limit=Decimal(lim), current_debt=Decimal(debt),
        )
        test_db.add(c)
    await test_db.commit()

    with_debt = await client.get(
        "/api/v1/customers", headers=admin_headers, params={"has_debt": "true"}
    )
    assert with_debt.json()["total"] == 2

    over = await client.get(
        "/api/v1/customers", headers=admin_headers, params={"over_limit": "true"}
    )
    assert over.json()["total"] == 1
    assert over.json()["items"][0]["name"] == "over"


async def test_sales_user_can_read_but_not_delete(
    client: AsyncClient, admin_headers: dict[str, str], sales_headers: dict[str, str]
) -> None:
    cust = (await client.post(
        "/api/v1/customers", headers=admin_headers, json={"name": "Z"}
    )).json()
    # sales can read
    r = await client.get(
        f"/api/v1/customers/{cust['id']}", headers=sales_headers
    )
    assert r.status_code == 200
    # sales cannot delete
    d = await client.delete(
        f"/api/v1/customers/{cust['id']}", headers=sales_headers
    )
    assert d.status_code == 403
    assert "customer:delete" in d.json()["detail"]


# ============ Contacts ============

@pytest.fixture
async def customer_id(client: AsyncClient, admin_headers: dict[str, str]) -> str:
    r = await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "Test Mijoz"},
    )
    return r.json()["id"]


async def test_add_and_list_contacts(
    client: AsyncClient, admin_headers: dict[str, str], customer_id: str
) -> None:
    a = await client.post(
        f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers,
        json={"full_name": "Alisher Karimov", "position": "Direktor", "phone": "+998901234567", "is_primary": True},
    )
    assert a.status_code == 201
    b = await client.post(
        f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers,
        json={"full_name": "Bobur Ali", "position": "Buxgalter"},
    )
    assert b.status_code == 201

    listed = await client.get(
        f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers
    )
    items = listed.json()
    assert len(items) == 2
    # is_primary birinchi
    assert items[0]["full_name"] == "Alisher Karimov" and items[0]["is_primary"] is True


async def test_setting_new_primary_unsets_old(
    client: AsyncClient, admin_headers: dict[str, str], customer_id: str
) -> None:
    await client.post(
        f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers,
        json={"full_name": "A", "is_primary": True},
    )
    await client.post(
        f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers,
        json={"full_name": "B", "is_primary": True},
    )
    listed = (await client.get(
        f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers
    )).json()
    primaries = [c for c in listed if c["is_primary"]]
    assert len(primaries) == 1 and primaries[0]["full_name"] == "B"


# ============ Interactions ============

async def test_add_interaction_with_default_occurred_at(
    client: AsyncClient, admin_headers: dict[str, str], customer_id: str
) -> None:
    r = await client.post(
        f"/api/v1/customers/{customer_id}/interactions", headers=admin_headers,
        json={
            "type": "call",
            "subject": "Yangi buyurtma haqida",
            "notes": "30 daqiqa suhbat",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "call" and body["subject"] == "Yangi buyurtma haqida"
    assert body["occurred_at"] is not None


async def test_interactions_filter_by_type(
    client: AsyncClient, admin_headers: dict[str, str], customer_id: str
) -> None:
    for t, s in [("call", "Q1"), ("call", "Q2"), ("meeting", "M1"), ("email", "E1")]:
        await client.post(
            f"/api/v1/customers/{customer_id}/interactions",
            headers=admin_headers,
            json={"type": t, "subject": s},
        )
    calls = await client.get(
        f"/api/v1/customers/{customer_id}/interactions",
        headers=admin_headers, params={"type": "call"},
    )
    assert calls.json()["total"] == 2


# ============ Balance ============

async def test_balance_aggregates_correctly(
    client: AsyncClient, admin_headers: dict[str, str], customer_id: str,
    test_db: AsyncSession,
) -> None:
    # Mijozga kredit limit va qarz beramiz
    import uuid as _uuid
    c = await test_db.get(Customer, _uuid.UUID(customer_id))
    c.credit_limit = Decimal("1000")
    c.current_debt = Decimal("250")
    await test_db.commit()

    # 2 ta kontakt, 1 ta primary
    for fn, primary in [("A", True), ("B", False)]:
        await client.post(
            f"/api/v1/customers/{customer_id}/contacts", headers=admin_headers,
            json={"full_name": fn, "is_primary": primary},
        )
    # 3 ta interaction
    for t, s in [("call", "Q1"), ("meeting", "M1"), ("call", "Q2")]:
        await client.post(
            f"/api/v1/customers/{customer_id}/interactions", headers=admin_headers,
            json={"type": t, "subject": s},
        )

    r = await client.get(
        f"/api/v1/customers/{customer_id}/balance", headers=admin_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Decimal serializatsiyasi DB dialect'iga bog'liq — qiymat bo'yicha tekshiramiz
    assert Decimal(body["credit_limit"]) == Decimal("1000")
    assert Decimal(body["current_debt"]) == Decimal("250")
    assert Decimal(body["available_credit"]) == Decimal("750")
    assert body["is_blocked"] is False
    assert body["contacts_total"] == 2
    assert body["primary_contact_name"] == "A"
    assert body["interactions_total"] == 3
    assert body["last_interaction_type"] in {"call", "meeting"}  # vaqt yaqin


async def test_balance_blocked_when_debt_reaches_limit(
    client: AsyncClient, admin_headers: dict[str, str], customer_id: str,
    test_db: AsyncSession,
) -> None:
    import uuid as _uuid
    c = await test_db.get(Customer, _uuid.UUID(customer_id))
    c.credit_limit = Decimal("500")
    c.current_debt = Decimal("500")
    await test_db.commit()

    r = await client.get(
        f"/api/v1/customers/{customer_id}/balance", headers=admin_headers
    )
    assert r.json()["is_blocked"] is True
    assert Decimal(r.json()["available_credit"]) == Decimal("0")
