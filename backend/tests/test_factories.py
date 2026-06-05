"""factories.py uchun smoke testlar — har factory'ning DB'ga yozish va asosiy
qiymatlar to'g'ri o'rnatilishini tekshiradi."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import AccountType
from app.models.customer import CustomerSegment
from app.models.product import Gender
from tests.factories import (
    make_account,
    make_brand,
    make_category,
    make_customer,
    make_product,
    make_supplier,
    make_variant,
    make_warehouse,
)


async def test_make_category(test_db: AsyncSession) -> None:
    c = await make_category(test_db, name="Maykalar")
    assert c.id is not None and c.name == "Maykalar"


async def test_make_product_with_auto_category(test_db: AsyncSession) -> None:
    p = await make_product(test_db, name="Mayka", gender=Gender.MEN)
    assert p.gender == Gender.MEN
    assert p.category_id is not None  # auto-created
    assert p.sku_prefix.endswith("-001")


async def test_make_variant_links_product(test_db: AsyncSession) -> None:
    p = await make_product(test_db)
    v = await make_variant(test_db, product_id=p.id, size="L", wholesale_price=Decimal("2500"))
    assert v.product_id == p.id
    assert v.size == "L"
    assert v.wholesale_price == Decimal("2500")


async def test_make_warehouse_brand_supplier(test_db: AsyncSession) -> None:
    w = await make_warehouse(test_db)
    b = await make_brand(test_db, name="Nike")
    s = await make_supplier(test_db, name="Asia", rating=5)
    assert w.id and b.id and s.id
    assert s.rating == 5


async def test_make_customer_account(test_db: AsyncSession) -> None:
    c = await make_customer(
        test_db, name="VIP", segment=CustomerSegment.VIP, credit_limit=Decimal("10000")
    )
    a = await make_account(
        test_db, name="Kassa", type_=AccountType.CASH, initial_balance=Decimal("500")
    )
    assert c.segment == CustomerSegment.VIP
    assert c.credit_limit == Decimal("10000")
    assert a.type == AccountType.CASH
    assert a.balance == Decimal("500")
